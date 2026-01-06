"""GenericSupervisor - Generic Supervisor.

Has no node-specific routing logic, determines routing via
Registry trigger conditions and LLM.
"""
from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field

from langchain_core.language_models import BaseChatModel

from agent_contracts.registry import NodeRegistry, get_node_registry
from agent_contracts.config import get_config
from agent_contracts.utils.logging import get_logger

logger = get_logger("agent_contracts.supervisor")


class SupervisorDecision(BaseModel):
    """Supervisor decision result."""
    next_node: str = Field(description="Next node name, or 'done'")
    reasoning: str = Field(default="", description="Decision reasoning")


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
    ):
        """Initialize.
        
        Args:
            supervisor_name: Supervisor type
            llm: LangChain LLM
            registry: Node registry (uses global if omitted)
            max_iterations: Max iterations (uses config if omitted)
            terminal_response_types: Terminal response types (uses config if omitted)
        """
        self.name = supervisor_name
        self.llm = llm
        self.registry = registry or get_node_registry()
        self.logger = logger
        
        # Load from config or use defaults
        config = get_config()
        self.max_iterations = max_iterations or config.supervisor.max_iterations
        self.terminal_response_types = terminal_response_types or set(
            config.supervisor.terminal_response_types
        )
    
    async def run(self, state: dict) -> dict:
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
        decision = await self.decide(state)
        
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
    
    async def decide(self, state: dict) -> SupervisorDecision:
        """Determine next node.
        
        1. Immediate exit check (response_type check)
        2. Rule-based evaluation (collect candidates)
        3. LLM decision (final decision)
           If no LLM, use top rule-based candidate
        """
        # Phase 0: Immediate exit check
        immediate = self._check_immediate_rules(state)
        if immediate:
            return SupervisorDecision(next_node=immediate, reasoning="Immediate rule")
        
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
                return SupervisorDecision(
                    next_node=node_id,
                    reasoning=f"Explicit routing to question owner: {node_id}"
                )

        # Phase 1: Rule-based evaluation
        rule_candidates = self.registry.evaluate_triggers(self.name, state)
        
        # Child node suggestion
        internal = state.get("_internal", {})
        previous_decision = internal.get("decision")
        
        child_decision = None
        if previous_decision and previous_decision != "done":
            child_decision = previous_decision
        
        # Phase 2: LLM decision
        if self.llm:
            decision = await self._decide_with_llm(state, rule_candidates, child_decision)
            if decision:
                return decision
        
        # Phase 3: Fallback
        if rule_candidates:
            return SupervisorDecision(
                next_node=rule_candidates[0],
                reasoning="Rule-based match (fallback)"
            )
        
        if child_decision:
             return SupervisorDecision(
                next_node=child_decision,
                reasoning="Child node suggestion (fallback)"
            )
            
        return SupervisorDecision(next_node="done", reasoning="No matching rule, defaulting to done")
    
    def _check_immediate_rules(self, state: dict) -> str | None:
        """Check if should exit immediately.
        
        Returns 'done' for user input waiting or final states.
        """
        response = state.get("response", {})
        response_type = response.get("response_type")
        
        if response_type in self.terminal_response_types:
            return "done"
        
        return None
    
    async def _decide_with_llm(
        self, 
        state: dict,
        rule_candidates: list[str],
        child_decision: str | None
    ) -> SupervisorDecision | None:
        """Decide using LLM."""
        try:
            prompt = self.registry.build_llm_prompt(self.name, state)
            
            # Add current state info
            request = state.get("request", {})
            
            context = f"""
Current action: {request.get('action', 'unknown')}
User message: {request.get('message', 'None')}

High priority system rules suggest: {rule_candidates[:3]}
Last active node suggested: {child_decision or 'None'}
"""
            full_prompt = f"{prompt}\n\nContext:\n{context}"
            
            # Use LangChain structured output
            structured_llm = self.llm.with_structured_output(SupervisorDecision)
            result = await structured_llm.ainvoke(
                f"System: You are a decision-making supervisor for a {self.name} flow. "
                f"If 'High priority system rules' are provided, you MUST select one of them. "
                f"Otherwise, prioritize user intent.\n\n{full_prompt}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"LLM decision failed: {e}")
            return None
    
    async def __call__(self, state: dict) -> dict:
        """LangGraph-compatible Callable."""
        return await self.run(state)
