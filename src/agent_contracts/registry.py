"""NodeRegistry - Node registration and management.

Registers all ModularNodes and provides routing map generation,
data flow analysis, and graph construction support.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_contracts.contracts import NodeContract, TriggerCondition
from agent_contracts.utils.logging import get_logger

logger = get_logger("agent_contracts.registry")


@dataclass
class TriggerMatch:
    """Represents a matched trigger condition.
    
    Attributes:
        priority: Priority of the matched condition
        node_name: Name of the matched node
        condition_index: Index of the matched condition in the node's trigger_conditions list
    """
    priority: int
    node_name: str
    condition_index: int


class NodeRegistry:
    """Registry for node registration and management.
    
    Example:
        registry = NodeRegistry()
        registry.register(OrderProcessorNode)
        registry.register(InventoryUpdaterNode)
        
        # Supervisor routing
        candidates = registry.evaluate_triggers("orders", state)
    """
    
    def __init__(self, valid_slices: set[str] | None = None):
        """Initialize registry.
        
        Args:
            valid_slices: Valid slice names for validation.
                         Defaults to basic set if not provided.
        """
        self._nodes: dict[str, type] = {}  # name -> node class
        self._contracts: dict[str, NodeContract] = {}  # name -> contract
        self._valid_slices = valid_slices or {"request", "response", "_internal"}
    
    def register(self, node_class: type) -> None:
        """Register a node class.
        
        Args:
            node_class: ModularNode subclass with CONTRACT
        """
        if not hasattr(node_class, "CONTRACT"):
            raise ValueError(f"Node class {node_class.__name__} must have CONTRACT")
        
        contract = node_class.CONTRACT
        self._validate_contract(contract)
        
        if contract.name in self._nodes:
            raise ValueError(f"Node {contract.name} is already registered")
            
        self._nodes[contract.name] = node_class
        self._contracts[contract.name] = contract
        
        logger.info(f"Registered node: {contract.name} (supervisor={contract.supervisor})")
    
    def _validate_contract(self, contract: NodeContract) -> None:
        """Validate contract consistency."""
        for slice_name in contract.reads:
            if slice_name not in self._valid_slices:
                logger.warning(f"Unknown slice in reads: {slice_name}")
        
        for slice_name in contract.writes:
            if slice_name not in self._valid_slices:
                logger.warning(f"Unknown slice in writes: {slice_name}")
            if slice_name == "request":
                logger.warning("Writing to 'request' slice is discouraged")
    
    def add_valid_slice(self, slice_name: str) -> None:
        """Add a valid slice name."""
        self._valid_slices.add(slice_name)
    
    def get_node_class(self, name: str) -> type | None:
        """Get node class by name."""
        return self._nodes.get(name)
    
    def get_contract(self, name: str) -> NodeContract | None:
        """Get contract by name."""
        return self._contracts.get(name)
    
    def get_all_nodes(self) -> list[str]:
        """Get all node names."""
        return list(self._nodes.keys())
    
    def get_supervisor_nodes(self, supervisor: str) -> list[str]:
        """Get node names belonging to a supervisor."""
        return [
            name for name, contract in self._contracts.items()
            if contract.supervisor == supervisor
        ]

    def export_contracts(self) -> dict[str, dict[str, Any]]:
        """Export registered contracts as serializable dicts.
        
        Returns:
            Mapping of node name -> contract dict
        """
        exported: dict[str, dict[str, Any]] = {}
        for name, contract in self._contracts.items():
            exported[name] = contract.model_dump()
        return exported
    
    # =========================================================================
    # Routing Evaluation
    # =========================================================================
    
    def evaluate_triggers(
        self,
        supervisor: str,
        state: dict,
    ) -> list[TriggerMatch]:
        """Evaluate all node trigger conditions and return matches.
        
        For each node, evaluates all trigger conditions and selects the one
        with the highest priority among matching conditions.
        
        Args:
            supervisor: Supervisor name to evaluate
            state: Current State
            
        Returns:
            List of TriggerMatch objects sorted by priority (descending)
        """
        matches: list[TriggerMatch] = []
        
        for name in self.get_supervisor_nodes(supervisor):
            contract = self._contracts[name]
            
            # Find highest priority matching condition for this node
            best_match: TriggerMatch | None = None
            for idx, condition in enumerate(contract.trigger_conditions):
                if self._evaluate_condition(condition, state):
                    if best_match is None or condition.priority > best_match.priority:
                        best_match = TriggerMatch(
                            priority=condition.priority,
                            node_name=name,
                            condition_index=idx,
                        )
            
            if best_match:
                matches.append(best_match)
        
        # Sort by priority (descending)
        return sorted(matches, key=lambda x: x.priority, reverse=True)
    
    def _evaluate_condition(
        self,
        condition: TriggerCondition,
        state: dict,
    ) -> bool:
        """Evaluate a single trigger condition."""
        def matches_expected(actual: Any, expected: Any) -> bool:
            if expected is True:
                return bool(actual) is True
            if expected is False:
                return bool(actual) is False
            return actual == expected

        # when conditions
        if condition.when:
            for key, expected in condition.when.items():
                actual = self._get_state_value(state, key)
                if not matches_expected(actual, expected):
                    return False
        
        # when_not conditions
        if condition.when_not:
            for key, unexpected in condition.when_not.items():
                actual = self._get_state_value(state, key)
                if matches_expected(actual, unexpected):
                    return False
        
        return True
    
    def _get_state_value(self, state: dict, key: str) -> Any:
        """Get value from State.
        
        Key format: "slice.field" / "slice.nested.field" or "field"
        """
        if "." in key:
            parts = key.split(".")
            slice_name = parts[0]
            value: Any = state.get(slice_name, {})
            for part in parts[1:]:
                if not isinstance(value, dict):
                    return None
                value = value.get(part)
            return value
        else:
            # Flat key: search all slices
            preferred_order = ["request", "response", "_internal"]
            ordered_slices = [
                s for s in preferred_order if s in self._valid_slices
            ] + sorted(self._valid_slices - set(preferred_order))

            for slice_name in ordered_slices:
                slice_data = state.get(slice_name, {})
                if isinstance(slice_data, dict) and key in slice_data:
                    return slice_data[key]
            return None
    
    # =========================================================================
    # LLM Prompt Generation
    # =========================================================================
    
    def build_llm_prompt(
        self,
        supervisor: str,
        state: dict,
        context: str | None = None,
    ) -> str:
        """Generate LLM prompt for Supervisor.
        
        Aggregates LLM hints from each node to build prompt.
        Optionally includes context information for better decision-making.
        
        Args:
            supervisor: Supervisor name
            state: Current state (for future use)
            context: Optional context string to include in prompt
            
        Returns:
            Complete LLM prompt with instructions and context
        """
        lines = ["Choose the next action based on the current state:\n"]
        
        # Add available actions
        for name in self.get_supervisor_nodes(supervisor):
            contract = self._contracts[name]
            hints = contract.get_llm_hints()
            
            if hints:
                hint_text = "; ".join(hints)
                lines.append(f"- **{name}**: {contract.description} ({hint_text})")
            else:
                lines.append(f"- **{name}**: {contract.description}")
        
        lines.append("\n- **done**: Complete the current flow\n")
        
        # Add context if provided
        if context:
            lines.append("\n## Current Context\n")
            lines.append(context)
            lines.append("")
        
        lines.append("Return only the action name.")
        
        return "\n".join(lines)
    
    # =========================================================================
    # Data Flow Analysis
    # =========================================================================
    
    def analyze_data_flow(self) -> dict[str, list[str]]:
        """Analyze data flow dependencies between nodes.
        
        Returns:
            {node_name: [dependent_nodes], ...}
        """
        dependencies: dict[str, list[str]] = {}
        
        for name, contract in self._contracts.items():
            deps = []
            for other_name, other_contract in self._contracts.items():
                if other_name == name:
                    continue
                # If another node writes to slices I read, there's a dependency
                if set(contract.reads) & set(other_contract.writes):
                    deps.append(other_name)
            dependencies[name] = deps
        
        return dependencies


# =============================================================================
# Singleton
# =============================================================================

_registry: NodeRegistry | None = None


def get_node_registry() -> NodeRegistry:
    """Get global registry."""
    global _registry
    if _registry is None:
        _registry = NodeRegistry()
    return _registry


def reset_registry() -> None:
    """Reset registry (for testing)."""
    global _registry
    _registry = None
