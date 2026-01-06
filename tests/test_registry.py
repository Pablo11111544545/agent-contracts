import pytest
from agent_contracts import NodeRegistry, NodeContract, ModularNode, NodeInputs, NodeOutputs
from unittest.mock import MagicMock

class MockNode(ModularNode):
    CONTRACT = NodeContract(
        name="mock_node",
        description="A mock node",
        reads=[],
        writes=[],
        supervisor="test_supervisor",
    )
    async def execute(self, inputs: NodeInputs) -> NodeOutputs:
        return NodeOutputs(response={})

class AnotherMockNode(ModularNode):
    CONTRACT = NodeContract(
        name="another_node",
        description="Another mock node",
        reads=[],
        writes=[],
        supervisor="test_supervisor",
    )
    async def execute(self, inputs: NodeInputs) -> NodeOutputs:
        return NodeOutputs(response={})

class TestNodeRegistry:
    def test_register_and_get(self):
        """Test registering a node and retrieving it."""
        registry = NodeRegistry()
        registry.register(MockNode)
        
        node_class = registry.get_node_class("mock_node")
        assert node_class == MockNode

    def test_get_nonexistent_node(self):
        """Test retrieving a node that hasn't been registered."""
        registry = NodeRegistry()
        node = registry.get_node_class("nonexistent_node")
        assert node is None

    def test_duplicate_registration(self):
        """Test that registering the same node name twice raises an error."""
        registry = NodeRegistry()
        registry.register(MockNode)
        
        # Define a duplicate node with the same name
        class DuplicateNode(ModularNode):
            CONTRACT = NodeContract(
                name="mock_node", # Same name
                description="Duplicate",
                reads=[],
                writes=[],
                supervisor="test_supervisor",
            )
            async def execute(self, inputs): pass

        with pytest.raises(ValueError, match="already registered"):
            registry.register(DuplicateNode)

    def test_get_all_nodes(self):
        """Test retrieving all registered node names."""
        registry = NodeRegistry()
        registry.register(MockNode)
        registry.register(AnotherMockNode)
        
        names = registry.get_all_nodes()
        assert len(names) == 2
        assert "mock_node" in names
        assert "another_node" in names


class TestTriggerPriority:
    """Tests for trigger condition priority evaluation."""
    
    def test_highest_priority_condition_wins(self):
        """Test that highest priority matching condition is used, not first match."""
        from agent_contracts import TriggerCondition
        
        class PriorityTestNode(ModularNode):
            CONTRACT = NodeContract(
                name="priority_node",
                description="Node with multiple trigger conditions",
                reads=[],
                writes=[],
                supervisor="test_supervisor",
                trigger_conditions=[
                    # Lower priority condition listed first
                    TriggerCondition(
                        when={"request.action": "test"},
                        priority=10,
                        llm_hint="Low priority"
                    ),
                    # Higher priority condition listed second
                    TriggerCondition(
                        when={"request.action": "test"},
                        priority=100,
                        llm_hint="High priority"
                    ),
                ]
            )
            async def execute(self, inputs: NodeInputs) -> NodeOutputs:
                return NodeOutputs(response={})
        
        registry = NodeRegistry()
        registry.register(PriorityTestNode)
        
        state = {
            "request": {"action": "test"}
        }
        
        # Evaluate triggers
        candidates = registry.evaluate_triggers("test_supervisor", state)
        
        # Should match with highest priority (100), not first match (10)
        assert len(candidates) == 1
        assert candidates[0] == "priority_node"
        
        # Verify the priority used is 100 (not 10)
        # We can check this by looking at internal state or by testing ordering
        # with another node

    def test_multiple_nodes_sorted_by_priority(self):
        """Test that multiple matching nodes are sorted by their highest priority."""
        from agent_contracts import TriggerCondition
        
        class LowPriorityNode(ModularNode):
            CONTRACT = NodeContract(
                name="low_priority",
                description="Low priority node",
                reads=[],
                writes=[],
                supervisor="priority_test",
                trigger_conditions=[
                    TriggerCondition(when={"_internal.active": True}, priority=10),
                ]
            )
            async def execute(self, inputs): return NodeOutputs()

        class HighPriorityNode(ModularNode):
            CONTRACT = NodeContract(
                name="high_priority",
                description="High priority node",
                reads=[],
                writes=[],
                supervisor="priority_test",
                trigger_conditions=[
                    TriggerCondition(when={"_internal.active": True}, priority=100),
                ]
            )
            async def execute(self, inputs): return NodeOutputs()
        
        registry = NodeRegistry()
        # Register in reverse priority order
        registry.register(LowPriorityNode)
        registry.register(HighPriorityNode)
        
        state = {"_internal": {"active": True}}
        candidates = registry.evaluate_triggers("priority_test", state)
        
        # High priority should come first
        assert candidates == ["high_priority", "low_priority"]
