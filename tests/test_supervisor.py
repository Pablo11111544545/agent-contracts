import pytest
from unittest.mock import MagicMock, AsyncMock
from agent_contracts import GenericSupervisor, NodeContract, TriggerCondition
from langchain_core.messages import AIMessage

@pytest.fixture
def mock_registry():
    """Fixture providing a registry with some mock contracts."""
    registry = MagicMock()
    
    contract1 = NodeContract(
        name="node1",
        description="Node 1",
        reads=[],
        writes=[],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(when={"action": "run_node1"}, priority=10)
        ]
    )
    
    contract2 = NodeContract(
        name="node2",
        description="Node 2",
        reads=[],
        writes=[],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(llm_hint="Run node 2 for search tasks")
        ]
    )
    
    registry.get_all_contracts.return_value = [contract1, contract2]
    return registry

@pytest.mark.asyncio
class TestGenericSupervisor:
    async def test_immediate_rule_match(self, mock_registry, mock_llm):
        """Test that a high-priority rule match bypasses the LLM."""
        # Mock evaluate_triggers to return a match
        mock_registry.evaluate_triggers.return_value = ["node1"]
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=mock_llm,
            registry=mock_registry
        )
        
        inputs = {
            "request": {"action": "run_node1"},
            "scratchpad": {"iteration": 0}
        }
        
        # Should pick node1 based on 'when' condition
        result = await supervisor.decide(inputs)
        assert result.next_node == "node1"
        
        # LLM should not have been called
        mock_llm.ainvoke.assert_not_called()

    async def test_max_iterations_reached(self, mock_registry, mock_llm):
        """Test that recursion limit returns END."""
        mock_registry.evaluate_triggers.return_value = []
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=mock_llm,
            registry=mock_registry,
            max_iterations=5
        )
        
        inputs = {
            "request": {},
            "scratchpad": {"iteration": 5} # Limit reached
        }
        
        result = await supervisor.run(inputs)
        assert result["_internal"]["decision"] == "done"

    async def test_llm_decision(self, mock_registry, mock_llm):
        """Test falling back to LLM decision."""
        # Mock evaluate_triggers to return empty so it falls back to LLM
        mock_registry.evaluate_triggers.return_value = []
        
        # Setup LLM to return a routing decision
        from agent_contracts.supervisor import SupervisorDecision
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            return_value=SupervisorDecision(
                next_node="node2",
                reasoning="User wants search"
            )
        )
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=mock_llm,
            registry=mock_registry
        )
        
        inputs = {
            "request": {"action": "search"},
            "scratchpad": {"iteration": 0}
        }
        
        result = await supervisor.decide(inputs)
        assert result.next_node == "node2"
