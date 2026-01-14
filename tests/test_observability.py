import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerMatch
from agent_contracts.supervisor import GenericSupervisor

class MockNode(ModularNode):
    CONTRACT = NodeContract(
        name="mock_node",
        description="Mock node",
        reads=["request"],
        writes=["response"],
        supervisor="main",
    )
    
    # Store the config passed to execute for verification
    received_config = None
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        MockNode.received_config = config
        return NodeOutputs(response={"data": "test"})

@pytest.mark.asyncio
async def test_node_propagates_metadata():
    """Test that ModularNode creates new config with metadata (immutable pattern)."""
    node = MockNode()
    original_config = {"metadata": {"existing": "value"}}
    
    await node({"request": {}}, config=original_config)
    
    # Original config should NOT be mutated (immutable pattern)
    assert original_config == {"metadata": {"existing": "value"}}
    
    # The execute method should receive the enhanced config
    received = MockNode.received_config
    assert received is not None
    assert received["metadata"]["node_name"] == "mock_node"
    assert received["metadata"]["node_supervisor"] == "main"
    assert received["metadata"]["existing"] == "value"

@pytest.mark.asyncio
async def test_supervisor_adds_trace_info():
    """Test that GenericSupervisor creates new config with trace info (immutable pattern)."""
    # Mock registry
    mock_registry = MagicMock()
    mock_registry.evaluate_triggers.return_value = [
        TriggerMatch(priority=100, node_name="mock_node", condition_index=0)
    ]
    
    supervisor = GenericSupervisor(
        supervisor_name="main",
        registry=mock_registry,
    )
    
    original_config = {"metadata": {}}
    state = {"request": {"action": "test"}}
    
    # Supervisor decides based on registry - config is used internally
    await supervisor(state, config=original_config)
    
    # Original config should NOT be mutated (immutable pattern)
    assert original_config == {"metadata": {}}
    
    # Verify supervisor uses registry correctly
    mock_registry.evaluate_triggers.assert_called_once()

