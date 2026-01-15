"""NodeContract - Node I/O contracts.

Each node defines a CONTRACT class variable to declare its
inputs, outputs, dependencies, and trigger conditions.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# Trigger Conditions
# =============================================================================

class TriggerCondition(BaseModel):
    """Condition for when a node should be triggered.
    
    The Supervisor collects matching conditions as hints for LLM decision.
    If no LLM is available, rule-based matching is used as fallback.
    """
    model_config = ConfigDict(frozen=True)
    
    # Priority (higher = evaluated first)
    priority: int = Field(default=0, description="Evaluation priority. Higher values are evaluated first.")
    
    # Rule-based conditions
    when: dict[str, Any] | None = Field(
        default=None,
        description="Match conditions. {slice.field: expected_value, ...}",
    )
    when_not: dict[str, Any] | None = Field(
        default=None,
        description="Non-match conditions. Matches when these are NOT true.",
    )
    
    # LLM decision hint
    llm_hint: str | None = Field(
        default=None,
        description="Hint for LLM when making routing decisions.",
    )


# =============================================================================
# Node Contract
# =============================================================================

class NodeContract(BaseModel):
    """Node I/O contract.
    
    Each node defines this as a CONTRACT class variable.
    Registry uses this for I/O validation, routing, and dependency analysis.
    
    Example:
        class OrderProcessorNode(ModularNode):
            CONTRACT = NodeContract(
                name="order_processor",
                description="Processes incoming orders",
                reads=["request", "orders", "inventory"],
                writes=["orders", "inventory", "response"],
                ...
            )
    """
    model_config = ConfigDict(frozen=True)
    
    # === Identification ===
    name: str = Field(description="Node name (key for graph registration)")
    description: str = Field(description="Node role description")
    
    # === I/O Definition (by slice) ===
    reads: list[str] = Field(
        description="List of slice names to read from"
    )
    writes: list[str] = Field(
        description="List of slice names to write to"
    )
    
    # === Dependencies ===
    requires_llm: bool = Field(
        default=False,
        description="Whether LLM client is required",
    )
    services: list[str] = Field(
        default_factory=list,
        description="Required service names (e.g., database_service, api_service)",
    )
    
    # === Supervisor ===
    supervisor: str = Field(
        description="Supervisor this node belongs to",
    )
    
    # === Trigger Conditions ===
    trigger_conditions: list[TriggerCondition] = Field(
        default_factory=list,
        description="List of conditions that trigger this node",
    )
    
    # === Terminal Condition ===
    is_terminal: bool = Field(
        default=False,
        description="Whether this node should transition to END after execution",
    )
    
    # === Visualization ===
    icon: str | None = Field(
        default=None,
        description="Optional emoji icon for visualization (e.g., '🔍', '💬')",
    )
    
    def get_highest_priority_condition(self) -> TriggerCondition | None:
        """Get the highest priority trigger condition."""
        if not self.trigger_conditions:
            return None
        return max(self.trigger_conditions, key=lambda c: c.priority)
    
    def get_llm_hints(self) -> list[str]:
        """Get all LLM hints."""
        return [c.llm_hint for c in self.trigger_conditions if c.llm_hint]


# =============================================================================
# I/O Types
# =============================================================================

class NodeInputs(BaseModel):
    """Node inputs.
    
    Holds slices extracted based on Contract.reads.
    """
    model_config = ConfigDict(extra="allow")  # Allow dynamic slice addition
    
    def get_slice(self, name: str) -> dict:
        """Get specified slice."""
        return getattr(self, name, {})


class NodeOutputs(BaseModel):
    """Node outputs.
    
    Holds slices to update based on Contract.writes.
    """
    model_config = ConfigDict(extra="allow")  # Allow dynamic slice addition
    
    def to_state_updates(self) -> dict[str, dict]:
        """Convert to State update dict."""
        return {k: v for k, v in self.model_dump().items() if v is not None}
