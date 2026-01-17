"""NodeContract - Node I/O contracts.

Each node defines a CONTRACT class variable to declare its
inputs, outputs, dependencies, and trigger conditions.
"""
from __future__ import annotations

from typing import Any
import logging

from pydantic import BaseModel, Field, ConfigDict, PrivateAttr

from agent_contracts.utils.logging import get_logger
from agent_contracts.errors import ContractViolationError


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

    _allowed_slices: set[str] = PrivateAttr(default_factory=set)
    _strict_contract_io: bool = PrivateAttr(default=False)
    _warn_contract_io: bool = PrivateAttr(default=True)
    _logger: logging.Logger = PrivateAttr(default_factory=lambda: get_logger("agent_contracts.contract_io"))
    _warned_reads: set[str] = PrivateAttr(default_factory=set)
    _node_name: str | None = PrivateAttr(default=None)
    
    def _configure_contract_io(
        self,
        *,
        allowed_slices: set[str],
        node_name: str | None,
        strict: bool,
        warn: bool,
        logger: logging.Logger | None = None,
    ) -> None:
        self._allowed_slices = set(allowed_slices)
        self._node_name = node_name
        self._strict_contract_io = strict
        self._warn_contract_io = warn
        if logger is not None:
            self._logger = logger

    def get_slice(self, name: str) -> dict:
        """Get specified slice."""
        if self._allowed_slices and name not in self._allowed_slices:
            node = self._node_name or "unknown"
            msg = f"Undeclared slice read '{name}' in node '{node}'"
            if self._strict_contract_io:
                raise ContractViolationError(msg)
            if self._warn_contract_io and name not in self._warned_reads:
                self._warned_reads.add(name)
                self._logger.warning(msg)
            return {}
        return getattr(self, name, {})


class NodeOutputs(BaseModel):
    """Node outputs.
    
    Holds slices to update based on Contract.writes.
    """
    model_config = ConfigDict(extra="allow")  # Allow dynamic slice addition
    
    def to_state_updates(self) -> dict[str, dict]:
        """Convert to State update dict."""
        return {k: v for k, v in self.model_dump().items() if v is not None}
