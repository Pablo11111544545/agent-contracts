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
