import pytest
from unittest.mock import MagicMock

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs
from agent_contracts.supervisor import GenericSupervisor

class MockNode(ModularNode):
    CONTRACT = NodeContract(
        name="mock_node",
        description="Mock node",
        reads=["request"],
        writes=["response"],
        supervisor="main",
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"data": "test"})

@pytest.mark.asyncio
async def test_node_propagates_metadata():
    """Test that ModularNode adds metadata to config."""
    node = MockNode()
    config = {"metadata": {"existing": "value"}}
    
    await node({"request": {}}, config=config)
    
    assert config["metadata"]["node_name"] == "mock_node"
    assert config["metadata"]["node_supervisor"] == "main"
    assert config["metadata"]["existing"] == "value"

@pytest.mark.asyncio
async def test_supervisor_adds_trace_info():
    """Test that GenericSupervisor adds trace info."""
    # Mock registry
    mock_registry = MagicMock()
    mock_registry.evaluate_triggers.return_value = [(100, "mock_node")]
    
    supervisor = GenericSupervisor(
        supervisor_name="main",
        registry=mock_registry,
    )
    
    config = {"metadata": {}}
    state = {"request": {"action": "test"}}
    
    await supervisor(state, config=config)
    
    assert config["metadata"]["supervisor_name"] == "main"
    assert "supervisor_decision" in config.get("tags", [])
