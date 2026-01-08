#!/usr/bin/env python3
"""
Example: Contract Validation
============================

Demonstrates the ContractValidator's ability to:
1. Detect unknown slices (ERROR)
2. Detect missing services (WARNING)
3. Report shared writers (INFO)

Run with:
    python examples/01_contract_validation.py
"""

import sys
sys.path.insert(0, "src")

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
    ContractValidator,
)
from agent_contracts.registry import NodeRegistry


# =============================================================================
# Example Nodes
# =============================================================================

class ValidNodeA(ModularNode):
    """A valid node that writes to response."""
    CONTRACT = NodeContract(
        name="node_a",
        description="First handler node",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=10,
                when={"request.action": "greet"},
                llm_hint="Handle greeting",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"message": "Hello!"})


class ValidNodeB(ModularNode):
    """Another valid node that also writes to response (shared slice)."""
    CONTRACT = NodeContract(
        name="node_b",
        description="Second handler node",
        reads=["request"],
        writes=["response"],  # Same slice as node_a (shared writers)
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=5,
                when={"request.action": "farewell"},
                llm_hint="Handle farewell",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"message": "Goodbye!"})


class NodeWithUnknownSlice(ModularNode):
    """A node with an unknown slice (ERROR case)."""
    CONTRACT = NodeContract(
        name="bad_slice_node",
        description="Node with unknown slice",
        reads=["invalid_slice"],  # This slice doesn't exist!
        writes=["response"],
        supervisor="main",
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"error": True})


class NodeWithUnknownService(ModularNode):
    """A node requiring an unknown service (WARNING case)."""
    CONTRACT = NodeContract(
        name="bad_service_node",
        description="Node requiring unknown service",
        reads=["request"],
        writes=["response"],
        services=["nonexistent_api"],  # Unknown service!
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(priority=1)
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class UnreachableNode(ModularNode):
    """A node with no trigger conditions (WARNING case)."""
    CONTRACT = NodeContract(
        name="unreachable_node",
        description="Node without trigger conditions",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[],  # No conditions!
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


# =============================================================================
# Demo
# =============================================================================

def demo_valid_nodes():
    """Demo: Valid nodes with shared writers."""
    print("=" * 60)
    print("Demo 1: Valid Nodes (Shared Writers Info)")
    print("=" * 60)
    
    registry = NodeRegistry()
    registry.register(ValidNodeA)
    registry.register(ValidNodeB)
    
    validator = ContractValidator(registry)
    result = validator.validate()
    
    print(result)
    print()
    
    # Show shared writers report
    shared = validator.get_shared_writers()
    print("Shared Writers Report:")
    for slice_name, writers in shared.items():
        if len(writers) > 1:
            print(f"  {slice_name}: {', '.join(writers)}")
    print()


def demo_unknown_slice():
    """Demo: Unknown slice detection (ERROR)."""
    print("=" * 60)
    print("Demo 2: Unknown Slice Detection (ERROR)")
    print("=" * 60)
    
    registry = NodeRegistry()
    registry.register(NodeWithUnknownSlice)
    
    validator = ContractValidator(registry)
    result = validator.validate()
    
    print(result)
    print()
    
    if result.has_errors:
        print("✗ Validation FAILED as expected!")
    print()


def demo_unknown_service():
    """Demo: Unknown service detection (WARNING)."""
    print("=" * 60)
    print("Demo 3: Unknown Service Detection (WARNING)")
    print("=" * 60)
    
    registry = NodeRegistry()
    registry.register(NodeWithUnknownService)
    
    # Provide known services
    validator = ContractValidator(
        registry,
        known_services={"db_service", "cache_service"},  # nonexistent_api is not here
    )
    result = validator.validate()
    
    print(result)
    print()


def demo_unreachable_node():
    """Demo: Unreachable node detection (WARNING)."""
    print("=" * 60)
    print("Demo 4: Unreachable Node Detection (WARNING)")
    print("=" * 60)
    
    registry = NodeRegistry()
    registry.register(UnreachableNode)
    
    validator = ContractValidator(registry)
    result = validator.validate()
    
    print(result)
    print()


def main():
    """Run all demos."""
    print()
    print("🔍 ContractValidator Demo")
    print("=" * 60)
    print()
    
    demo_valid_nodes()
    demo_unknown_slice()
    demo_unknown_service()
    demo_unreachable_node()
    
    print("=" * 60)
    print("✅ All demos completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
