"""Routing types for traceable supervisor decisions.

These types provide structured, explainable routing decisions
for debugging and observability.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_contracts.supervisor import SupervisorDecision


# =============================================================================
# Traceable Routing Types
# =============================================================================

class MatchedRule(BaseModel):
    """A matched trigger condition.
    
    Represents a single rule that matched during supervisor evaluation.
    
    Attributes:
        node: Node name that matched
        condition: Human-readable condition description
        priority: Trigger priority (higher = evaluated first)
    
    Example:
        rule = MatchedRule(
            node="search",
            condition="request.action=search",
            priority=100,
        )
    """
    node: str = Field(description="Node name")
    condition: str = Field(description="Human-readable condition description")
    priority: int = Field(description="Trigger priority")


class RoutingReason(BaseModel):
    """Detailed routing decision reason.
    
    Provides structured explanation of why a particular node was selected.
    
    Attributes:
        decision_type: Type of decision made
        matched_rules: List of rules that matched
        llm_used: Whether LLM was used for the decision
        llm_reasoning: LLM's reasoning if used
    
    Decision Types:
        - terminal_state: Response type triggered exit
        - explicit_routing: Answer routed to question owner
        - rule_match: TriggerCondition matched
        - llm_decision: LLM made the choice
        - fallback: No match, using default
    """
    decision_type: str = Field(
        description="Type of decision: terminal_state, explicit_routing, rule_match, llm_decision, fallback"
    )
    matched_rules: list[MatchedRule] = Field(
        default_factory=list,
        description="List of matched trigger rules"
    )
    llm_used: bool = Field(default=False, description="Whether LLM was used for decision")
    llm_reasoning: str | None = Field(default=None, description="LLM's reasoning if used")


class RoutingDecision(BaseModel):
    """Complete routing decision with traceability.
    
    The main output of `GenericSupervisor.decide_with_trace()`.
    Provides full visibility into how a routing decision was made.
    
    Attributes:
        selected_node: The node that was selected
        reason: Detailed reason for the decision
    
    Example:
        decision = await supervisor.decide_with_trace(state)
        
        print(f"Selected: {decision.selected_node}")
        print(f"Type: {decision.reason.decision_type}")
        
        for rule in decision.reason.matched_rules:
            print(f"  P{rule.priority}: {rule.node} - {rule.condition}")
    """
    selected_node: str = Field(description="Selected node name")
    reason: RoutingReason = Field(description="Decision reason details")
    
    def to_supervisor_decision(self) -> "SupervisorDecision":
        """Convert to SupervisorDecision for backward compatibility.
        
        Returns:
            SupervisorDecision with condensed reasoning string
        """
        # Import here to avoid circular dependency
        from agent_contracts.supervisor import SupervisorDecision
        
        reasoning_parts = [self.reason.decision_type]
        if self.reason.matched_rules:
            rules_str = ", ".join(r.node for r in self.reason.matched_rules)
            reasoning_parts.append(f"candidates: [{rules_str}]")
        if self.reason.llm_used:
            reasoning_parts.append("LLM")
        return SupervisorDecision(
            next_node=self.selected_node,
            reasoning=" | ".join(reasoning_parts)
        )
