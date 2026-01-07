import pytest
from unittest.mock import MagicMock, AsyncMock
from agent_contracts import GenericSupervisor, NodeContract, TriggerCondition

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
    registry.get_supervisor_nodes.return_value = ["node1", "node2"]
    return registry

@pytest.mark.asyncio
class TestGenericSupervisor:
    async def test_rule_candidate_with_llm(self, mock_registry, mock_llm):
        """Test that rule candidates are passed to LLM for final decision."""
        # Mock evaluate_triggers to return a rule candidate
        mock_registry.evaluate_triggers.return_value = [(10, "node1")]
        mock_registry.build_llm_prompt.return_value = "Choose next action"
        
        # Setup LLM to return the rule candidate
        from agent_contracts.supervisor import SupervisorDecision
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            return_value=SupervisorDecision(
                next_node="node1",
                reasoning="Rule match for run_node1"
            )
        )
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=mock_llm,
            registry=mock_registry
        )
        
        inputs = {
            "request": {"action": "run_node1"},
            "_internal": {"main_iteration": 0}
        }
        
        result = await supervisor.decide(inputs)
        assert result.next_node == "node1"

    async def test_max_iterations_reached(self, mock_registry, mock_llm):
        """Test that max iterations returns done."""
        mock_registry.evaluate_triggers.return_value = []
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=mock_llm,
            registry=mock_registry,
            max_iterations=5
        )
        
        inputs = {
            "request": {},
            "_internal": {"main_iteration": 5}  # Limit reached
        }
        
        result = await supervisor.run(inputs)
        assert result["_internal"]["decision"] == "done"

    async def test_llm_decision(self, mock_registry, mock_llm):
        """Test falling back to LLM decision when no rules match."""
        # Mock evaluate_triggers to return empty so it falls back to LLM
        mock_registry.evaluate_triggers.return_value = []
        mock_registry.build_llm_prompt.return_value = "Choose next action"
        
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
            "_internal": {"main_iteration": 0}
        }
        
        result = await supervisor.decide(inputs)
        assert result.next_node == "node2"
