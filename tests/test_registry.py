import pytest
from agent_contracts import NodeRegistry, TriggerMatch, NodeContract, ModularNode, NodeInputs, NodeOutputs

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
        matches = registry.evaluate_triggers("test_supervisor", state)
        
        # Should select the highest priority matching condition (priority 100)
        # even though it's listed second in the trigger_conditions list
        assert len(matches) == 1
        assert matches[0].node_name == "priority_node"
        assert matches[0].priority == 100  # Highest priority
        assert matches[0].condition_index == 1  # Second condition (index 1)

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
        matches = registry.evaluate_triggers("priority_test", state)
        
        # High priority should come first
        assert len(matches) == 2
        assert matches[0].node_name == "high_priority"
        assert matches[0].priority == 100
        assert matches[1].node_name == "low_priority"
        assert matches[1].priority == 10


class TestRegistryEdgeCases:
    """Tests for edge cases and additional registry functionality."""

    def test_register_without_contract(self):
        """Test that registering a class without CONTRACT raises error."""
        class NoContractNode:
            pass
        
        registry = NodeRegistry()
        with pytest.raises(ValueError, match="must have CONTRACT"):
            registry.register(NoContractNode)

    def test_unknown_slice_warning(self):
        """Test that unknown slices in reads/writes log warnings."""
        class UnknownSliceNode(ModularNode):
            CONTRACT = NodeContract(
                name="unknown_slice_node",
                description="Node with unknown slices",
                reads=["unknown_read_slice"],
                writes=["unknown_write_slice"],
                supervisor="test",
            )
            async def execute(self, inputs): return NodeOutputs()
        
        registry = NodeRegistry()
        # Should not raise, just log warnings
        registry.register(UnknownSliceNode)
        
        contract = registry.get_contract("unknown_slice_node")
        assert contract is not None

    def test_request_write_warning(self):
        """Test that writing to request slice logs warning."""
        class RequestWriteNode(ModularNode):
            CONTRACT = NodeContract(
                name="request_writer",
                description="Writes to request",
                reads=["request"],
                writes=["request"],
                supervisor="test",
            )
            async def execute(self, inputs): return NodeOutputs()
        
        registry = NodeRegistry()
        # Should not raise, just log warning
        registry.register(RequestWriteNode)

    def test_add_valid_slice(self):
        """Test adding valid slices to registry."""
        registry = NodeRegistry()
        registry.add_valid_slice("custom_slice")
        
        class CustomSliceNode(ModularNode):
            CONTRACT = NodeContract(
                name="custom_slice_node",
                description="Uses custom slice",
                reads=["custom_slice"],
                writes=["custom_slice"],
                supervisor="test",
            )
            async def execute(self, inputs): return NodeOutputs()
        
        # Should register without warnings about unknown slice
        registry.register(CustomSliceNode)

    def test_when_not_condition(self):
        """Test when_not condition evaluation."""
        from agent_contracts import TriggerCondition
        
        class WhenNotNode(ModularNode):
            CONTRACT = NodeContract(
                name="when_not_node",
                description="Node with when_not condition",
                reads=[],
                writes=[],
                supervisor="test",
                trigger_conditions=[
                    TriggerCondition(
                        when_not={"response.done": True},
                        priority=10,
                    ),
                ]
            )
            async def execute(self, inputs): return NodeOutputs()
        
        registry = NodeRegistry()
        registry.register(WhenNotNode)
        
        # Should match when done is not True
        state = {"response": {"done": False}}
        matches = registry.evaluate_triggers("test", state)
        assert len(matches) == 1
        
        # Should NOT match when done is True
        state = {"response": {"done": True}}
        matches = registry.evaluate_triggers("test", state)
        assert len(matches) == 0

    def test_build_llm_prompt_with_hints(self):
        """Test building LLM prompt with and without hints."""
        from agent_contracts import TriggerCondition
        
        class NodeWithHint(ModularNode):
            CONTRACT = NodeContract(
                name="with_hint",
                description="Has hint",
                reads=[],
                writes=[],
                supervisor="prompt_test",
                trigger_conditions=[
                    TriggerCondition(priority=10, llm_hint="Use this for X"),
                ]
            )
            async def execute(self, inputs): return NodeOutputs()
        
        class NodeWithoutHint(ModularNode):
            CONTRACT = NodeContract(
                name="without_hint",
                description="No hint",
                reads=[],
                writes=[],
                supervisor="prompt_test",
            )
            async def execute(self, inputs): return NodeOutputs()
        
        registry = NodeRegistry()
        registry.register(NodeWithHint)
        registry.register(NodeWithoutHint)
        
        prompt = registry.build_llm_prompt("prompt_test", {})
        
        assert "with_hint" in prompt
        assert "Use this for X" in prompt
        assert "without_hint" in prompt
        assert "done" in prompt

    def test_flat_key_search(self):
        """Test _get_state_value with flat key (no dot)."""
        registry = NodeRegistry()
        
        state = {
            "request": {"action": "test"},
            "response": {"type": "result"},
        }
        
        # Should find action in request
        assert registry._get_state_value(state, "action") == "test"
        # Should find type in response
        assert registry._get_state_value(state, "type") == "result"
        # Should return None for missing key
        assert registry._get_state_value(state, "missing") is None

    def test_nested_path_with_non_dict(self):
        """Test _get_state_value with nested path that hits non-dict."""
        registry = NodeRegistry()
        
        state = {
            "request": {"action": "test"},  # action is a string, not a dict
        }
        
        # Trying to access action.something should return None
        result = registry._get_state_value(state, "request.action.nested")
        assert result is None


class TestRegistrySingleton:
    """Tests for registry singleton functions."""

    def test_get_and_reset_registry(self):
        """Test get_node_registry and reset_registry functions."""
        from agent_contracts import get_node_registry
        from agent_contracts.registry import reset_registry
        
        # Get registry
        reg1 = get_node_registry()
        reg2 = get_node_registry()
        
        assert reg1 is reg2  # Same instance
        
        # Reset
        reset_registry()
        
        reg3 = get_node_registry()
        assert reg3 is not reg1  # New instance

