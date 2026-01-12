"""GenericSupervisor - Generic Supervisor.

Has no node-specific routing logic, determines routing via
Registry trigger conditions and LLM.
"""
from __future__ import annotations

import json
from typing import Any, Optional, Protocol

from pydantic import BaseModel, Field

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig

from agent_contracts.registry import NodeRegistry, get_node_registry
from agent_contracts.config import get_config
from agent_contracts.utils.logging import get_logger
from agent_contracts.routing import MatchedRule, RoutingReason, RoutingDecision

logger = get_logger("agent_contracts.supervisor")


class SupervisorDecision(BaseModel):
    """Supervisor decision result."""
    next_node: str = Field(description="Next node name, or 'done'")
    reasoning: str = Field(default="", description="Decision reasoning")


class ContextBuilder(Protocol):
    """Supervisor用のコンテキスト構築プロトコル。
    
    Allows customization of which state slices and additional context
    are passed to LLM for routing decisions.
    
    Example:
        def my_context_builder(state: dict, candidates: list[str]) -> dict:
            return {
                "slices": {"request", "response", "_internal", "conversation"},
                "summary": {
                    "total_turns": len(state.get("conversation", {}).get("messages", [])),
                    "readiness": 0.67,
                }
            }
        
        supervisor = GenericSupervisor(
            supervisor_name="shopping",
            llm=llm,
            context_builder=my_context_builder,
        )
    """
    
    def __call__(
        self,
        state: dict,
        candidates: list[str],
    ) -> dict:
        """Build context for LLM routing decision.
        
        Args:
            state: Current agent state
            candidates: List of candidate node names from trigger evaluation
            
        Returns:
            Dictionary with:
                - "slices" (set[str]): Set of slice names to include in LLM context
                - "summary" (dict | None): Optional additional context summary
        """
        ...


class GenericSupervisor:
    """Generic Supervisor.
    
    Has no node-specific rule-based logic,
    evaluates conditions from NodeRegistry.
    
    Example:
        supervisor = GenericSupervisor("shopping", llm=llm)
        decision = await supervisor.decide(state)
    """
    
    def __init__(
        self,
        supervisor_name: str,
        llm: BaseChatModel | None = None,
        registry: NodeRegistry | None = None,
        max_iterations: int | None = None,
        terminal_response_types: set[str] | None = None,
        context_builder: ContextBuilder | None = None,
    ):
        """Initialize.
        
        Args:
            supervisor_name: Supervisor type
            llm: LangChain LLM
            registry: Node registry (uses global if omitted)
            max_iterations: Max iterations (uses config if omitted)
            terminal_response_types: Terminal response types (uses config if omitted)
            context_builder: Custom context builder for LLM routing (optional).
                If provided, allows customization of which state slices and
                additional context are passed to LLM for routing decisions.
                If omitted, uses default behavior (request, response, _internal only).
        """
        self.name = supervisor_name
        self.llm = llm
        self.registry = registry or get_node_registry()
        self.logger = logger
        self.context_builder = context_builder
        
        # Load from config or use defaults
        config = get_config()
        self.max_iterations = max_iterations or config.supervisor.max_iterations
        self.terminal_response_types = terminal_response_types or set(
            config.supervisor.terminal_response_types
        )
    
    async def run(
        self,
        state: dict,
        config: Optional[RunnableConfig] = None,
    ) -> dict:
        """Execute Supervisor node.
        
        Called as LangGraph node.
        """
        # Iteration management
        internal = state.get("_internal", {})
        iteration_key = f"{self.name}_iteration"
        current_iteration = internal.get(iteration_key, 0)
        
        # Infinite loop prevention
        if current_iteration >= self.max_iterations:
            self.logger.warning(f"Max iterations ({self.max_iterations}) reached for {self.name}")
            return {
                "_internal": {
                    **internal,
                    "decision": "done",
                    iteration_key: current_iteration,
                }
            }
        
        # Decide
        decision = await self.decide(state, config)
        
        self.logger.info(
            f"{self.name} supervisor decision: {decision.next_node} ({decision.reasoning})"
        )
        
        return {
            "_internal": {
                **internal,
                "decision": decision.next_node,
                iteration_key: current_iteration + 1,
            }
        }
    
    async def decide(
        self,
        state: dict,
        config: Optional[RunnableConfig] = None,
    ) -> SupervisorDecision:
        """Determine next node.
        
        This is a convenience wrapper around decide_with_trace() that returns
        a simplified SupervisorDecision instead of the full RoutingDecision.
        
        For debugging and detailed routing information, use decide_with_trace().
        """
        routing_decision = await self.decide_with_trace(state, config)
        return routing_decision.to_supervisor_decision()
    
    def _check_immediate_rules(self, state: dict) -> str | None:
        """Check if should exit immediately.
        
        Returns 'done' for user input waiting or final states.
        """
        response = state.get("response", {})
        response_type = response.get("response_type")
        
        if response_type in self.terminal_response_types:
            return "done"
        
        return None
    
    def _select_top_matches(self, matches: list[tuple[int, str]]) -> list[str]:
        """Select top candidates handling ties (Top 3 + Ties)."""
        if not matches:
            return []
            
        selected = []
        limit = 3
        last_prio = -1
        
        for i, (prio, name) in enumerate(matches):
            if i < limit:
                selected.append(name)
                last_prio = prio
            elif prio == last_prio:
                selected.append(name)
            else:
                break
        return selected
    
    def _collect_context_slices(
        self,
        state: dict,
        rule_candidates: list[str],
    ) -> set[str]:
        """Collect state slices for LLM routing decision.
        
        If a custom context_builder is provided, uses it to determine which
        slices to include. Otherwise, uses minimal default context.
        
        Args:
            state: Current state
            rule_candidates: List of candidate node names from trigger evaluation
            
        Returns:
            Set of slice names to include in LLM context
        """
        if self.context_builder:
            result = self.context_builder(state, rule_candidates)
            return result.get("slices", {"request", "response", "_internal"})
        
        # Default behavior (backward compatible)
        return {"request", "response", "_internal"}
    
    
    def _format_rule_candidates_with_reasons(
        self,
        matches: list[tuple[int, str]],
        candidates: list[str],
    ) -> str:
        """Format rule candidates with match reasons for LLM context.
        
        Example output:
            - appearance_analyst (P95): matched because request.user_image=True
            - interview_strategy (P90): matched because request.request_action=create_card
        """
        if not candidates:
            return "(none)"
        
        lines = []
        for priority, node_name in matches:
            if node_name not in candidates:
                continue
            
            contract = self.registry.get_contract(node_name)
            if not contract:
                lines.append(f"- {node_name} (P{priority})")
                continue
            
            # Find the matching condition
            condition_str = ""
            for condition in contract.trigger_conditions:
                if condition.priority == priority:
                    if condition.when:
                        parts = [f"{k}={v}" for k, v in condition.when.items()]
                        condition_str = " AND ".join(parts)
                    elif condition.when_not:
                        parts = [f"NOT {k}={v}" for k, v in condition.when_not.items()]
                        condition_str = " AND ".join(parts)
                    else:
                        condition_str = "(always)"
                    break
            
            if condition_str:
                lines.append(f"- {node_name} (P{priority}): matched because {condition_str}")
            else:
                lines.append(f"- {node_name} (P{priority})")
        
        return "\n".join(lines) if lines else "(none)"
    
    async def _decide_with_llm(
        self,
        state: dict,
        matches: list[tuple[int, str]],
        rule_candidates: list[str],
        child_decision: str | None,
        config: Optional[RunnableConfig] = None,
    ) -> SupervisorDecision | None:
        """Decide using LLM with enriched context.
        
        Builds context from:
        1. Base slices (request, response, _internal) - directly serialized as JSON
        2. Rule match reasons
        3. Previous node suggestion
        """
        try:
            # Collect relevant slices and additional context from context_builder
            context_slices = {"request", "response", "_internal"}  # default
            additional_context = ""
            
            if self.context_builder:
                result = self.context_builder(state, rule_candidates)
                context_slices = result.get("slices", context_slices)
                
                # Handle summary - support both dict and string formats
                if result.get("summary"):
                    summary = result["summary"]
                    if isinstance(summary, str):
                        # Already formatted as string
                        additional_context = f"\n\nAdditional Context:\n{summary}"
                    else:
                        # Dict format - convert to JSON
                        summary_json = json.dumps(summary, ensure_ascii=False, default=str)
                        additional_context = f"\n\nAdditional Context:\n{summary_json}"
            
            # Build state summary using direct JSON serialization
            state_parts = []
            for slice_name in sorted(context_slices):
                if slice_name in state:
                    slice_json = json.dumps(state[slice_name], ensure_ascii=False, default=str)
                    state_parts.append(f"{slice_name}: {slice_json}")
            
            state_summary = "\n".join(state_parts) if state_parts else "(no state)"
            
            # Format candidates with match reasons
            candidates_with_reasons = self._format_rule_candidates_with_reasons(
                matches, rule_candidates
            )
            
            # Build full context
            context = f"""
Current State:
{state_summary}{additional_context}

High priority system rules suggest:
{candidates_with_reasons}

Last active node suggested: {child_decision or 'None'}
"""
            
            # Build prompt with context embedded
            prompt = self.registry.build_llm_prompt(self.name, state, context=context)
            
            # Use LangChain structured output
            structured_llm = self.llm.with_structured_output(SupervisorDecision)
            result = await structured_llm.ainvoke(
                f"System: You are a decision-making supervisor for a {self.name} flow. "
                f"If 'High priority system rules' are provided, you MUST select one of them. "
                f"Otherwise, prioritize user intent.\n\n{prompt}",
                config=config,
            )
            
            # Validate LLM decision against valid nodes
            valid_nodes = set(self.registry.get_supervisor_nodes(self.name))
            valid_nodes.add("done")
            
            if result.next_node not in valid_nodes:
                self.logger.warning(
                    f"LLM returned invalid node: {result.next_node}, "
                    f"valid nodes: {valid_nodes}"
                )
                # If rule candidates exist, use the top one
                if rule_candidates:
                    return SupervisorDecision(
                        next_node=rule_candidates[0],
                        reasoning=f"LLM returned invalid '{result.next_node}', using rule candidate"
                    )
                # Otherwise return None to trigger fallback
                return None
            
            return result
            
        except Exception as e:
            self.logger.error(f"LLM decision failed: {e}")
            return None
    
    def _build_matched_rules(
        self,
        matches: list[tuple[int, str]],
    ) -> list[MatchedRule]:
        """Build MatchedRule list from trigger matches."""
        matched_rules = []
        
        for priority, node_name in matches:
            contract = self.registry.get_contract(node_name)
            if not contract:
                continue
            
            # Find the matching condition description
            condition_str = ""
            for condition in contract.trigger_conditions:
                if condition.priority == priority:
                    if condition.when:
                        parts = [f"{k}={v}" for k, v in condition.when.items()]
                        condition_str = " AND ".join(parts)
                    elif condition.when_not:
                        parts = [f"NOT {k}={v}" for k, v in condition.when_not.items()]
                        condition_str = " AND ".join(parts)
                    else:
                        condition_str = "(always)"
                    break
            
            matched_rules.append(MatchedRule(
                node=node_name,
                condition=condition_str or "(unknown)",
                priority=priority,
            ))
        
        return matched_rules
    
    async def decide_with_trace(
        self,
        state: dict,
        config: Optional[RunnableConfig] = None,
    ) -> RoutingDecision:
        """Determine next node with full traceability.
        
        Returns RoutingDecision with detailed reasoning.
        Use this for debugging and explainability.
        
        Example:
            decision = await supervisor.decide_with_trace(state)
            print(f"Selected: {decision.selected_node}")
            print(f"Type: {decision.reason.decision_type}")
            for rule in decision.reason.matched_rules:
                print(f"  - {rule.node} (P{rule.priority}): {rule.condition}")
        """
        # Enhance trace config (create new config to avoid mutation)
        base_config = config or {}
        existing_metadata = base_config.get("metadata", {})
        existing_tags = base_config.get("tags", [])
        config = {
            **base_config,
            "metadata": {
                **existing_metadata,
                "supervisor_name": self.name,
                "supervisor_iteration": state.get("_internal", {}).get(f"{self.name}_iteration", 0),
            },
            "tags": [*existing_tags, "supervisor_decision"],
        }
        
        # Phase 0: Immediate exit check (terminal state)
        immediate = self._check_immediate_rules(state)
        if immediate:
            return RoutingDecision(
                selected_node=immediate,
                reason=RoutingReason(decision_type="terminal_state")
            )
        
        # Phase 0.5: Explicit Routing (Return to Sender)
        req = state.get("request", {})
        action = req.get("action") if isinstance(req, dict) else None
        
        if action == "answer":
            interview = state.get("interview", {})
            lq = interview.get("last_question") if isinstance(interview, dict) else None
            node_id = None
            if lq:
                if isinstance(lq, dict):
                    node_id = lq.get("node_id")
                else:
                    node_id = getattr(lq, "node_id", None)
            
            if node_id:
                return RoutingDecision(
                    selected_node=node_id,
                    reason=RoutingReason(decision_type="explicit_routing")
                )

        # Phase 1: Rule-based evaluation
        matches = self.registry.evaluate_triggers(self.name, state)
        matched_rules = self._build_matched_rules(matches)
        
        # Smart selection for LLM context (Top 3 + Ties)
        rule_candidates = self._select_top_matches(matches)
        
        # Child node suggestion
        internal = state.get("_internal", {})
        previous_decision = internal.get("decision")
        
        child_decision = None
        if previous_decision and previous_decision != "done":
            child_decision = previous_decision
        
        # Phase 2: LLM decision
        if self.llm:
            llm_result = await self._decide_with_llm(
                state,
                matches,
                rule_candidates,
                child_decision,
                config=config,
            )
            if llm_result:
                return RoutingDecision(
                    selected_node=llm_result.next_node,
                    reason=RoutingReason(
                        decision_type="llm_decision",
                        matched_rules=matched_rules,
                        llm_used=True,
                        llm_reasoning=llm_result.reasoning,
                    )
                )
        
        # Phase 3: Fallback
        if matches:
            return RoutingDecision(
                selected_node=matches[0][1],
                reason=RoutingReason(
                    decision_type="rule_match",
                    matched_rules=matched_rules,
                )
            )
        
        if child_decision:
            return RoutingDecision(
                selected_node=child_decision,
                reason=RoutingReason(decision_type="fallback")
            )
            
        return RoutingDecision(
            selected_node="done",
            reason=RoutingReason(decision_type="fallback")
        )
    
    async def __call__(
        self,
        state: dict,
        config: Optional[RunnableConfig] = None,
    ) -> dict:
        """LangGraph-compatible Callable."""
        return await self.run(state, config)
