"""NodeRegistry - Node registration and management.

Registers all ModularNodes and provides routing map generation,
data flow analysis, and graph construction support.
"""
from __future__ import annotations

from typing import Any, Callable

from agent_contracts.contracts import NodeContract, TriggerCondition
from agent_contracts.utils.logging import get_logger

logger = get_logger("agent_contracts.registry")


class NodeRegistry:
    """Registry for node registration and management.
    
    Example:
        registry = NodeRegistry()
        registry.register(LikeHandlerNode)
        registry.register(UnlikeHandlerNode)
        
        # Supervisor routing
        candidates = registry.evaluate_triggers("shopping", state)
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
                logger.warning(f"Writing to 'request' slice is discouraged")
    
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
    
    # =========================================================================
    # Routing Evaluation
    # =========================================================================
    
    def evaluate_triggers(
        self,
        supervisor: str,
        state: dict,
    ) -> list[tuple[int, str]]:
        """Evaluate all node trigger conditions and return matches.
        
        Args:
            supervisor: Supervisor name to evaluate
            state: Current State
            
        Returns:
            Matched node names (ordered by priority) as (priority, name) tuples
        """
        candidates: list[tuple[int, str]] = []
        
        for name in self.get_supervisor_nodes(supervisor):
            contract = self._contracts[name]
            
            # Find highest priority matching condition for this node
            highest_priority: int | None = None
            for condition in contract.trigger_conditions:
                if self._evaluate_condition(condition, state):
                    if highest_priority is None or condition.priority > highest_priority:
                        highest_priority = condition.priority
            
            if highest_priority is not None:
                candidates.append((highest_priority, name))
        
        # Sort by priority (descending)
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates
    
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
            for slice_name in list(self._valid_slices):
                slice_data = state.get(slice_name, {})
                if isinstance(slice_data, dict) and key in slice_data:
                    return slice_data[key]
            return None
    
    # =========================================================================
    # LLM Prompt Generation
    # =========================================================================
    
    def build_llm_prompt(self, supervisor: str, state: dict) -> str:
        """Generate LLM prompt for Supervisor.
        
        Aggregates LLM hints from each node to build prompt.
        """
        lines = ["Choose the next action based on the current state:\n"]
        
        for name in self.get_supervisor_nodes(supervisor):
            contract = self._contracts[name]
            hints = contract.get_llm_hints()
            
            if hints:
                hint_text = "; ".join(hints)
                lines.append(f"- **{name}**: {contract.description} ({hint_text})")
            else:
                lines.append(f"- **{name}**: {contract.description}")
        
        lines.append("\n- **done**: Complete the current flow\n")
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
