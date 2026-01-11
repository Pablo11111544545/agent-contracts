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
    registry.get_contract.side_effect = lambda name: {
        "node1": contract1,
        "node2": contract2,
    }.get(name)
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

    async def test_same_priority_nodes_included(self, mock_registry, mock_llm):
        """Test that nodes with same priority are all included."""
        # Multiple nodes with same priority
        mock_registry.evaluate_triggers.return_value = [
            (10, "node1"),
            (10, "node2"),  # Same priority
            (10, "node3"),  # Same priority
            (10, "node4"),  # Same priority (beyond limit but same priority)
        ]
        mock_registry.build_llm_prompt.return_value = "Choose"
        
        from agent_contracts.supervisor import SupervisorDecision
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            return_value=SupervisorDecision(next_node="node1", reasoning="")
        )
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=mock_llm,
            registry=mock_registry
        )
        
        inputs = {"request": {}, "_internal": {"main_iteration": 0}}
        result = await supervisor.decide(inputs)
        assert result.next_node == "node1"

    async def test_llm_returns_invalid_node_fallback_to_rule(self, mock_registry, mock_llm):
        """Test fallback when LLM returns invalid node."""
        mock_registry.evaluate_triggers.return_value = [(10, "node1")]
        mock_registry.build_llm_prompt.return_value = "Choose"
        
        from agent_contracts.supervisor import SupervisorDecision
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            return_value=SupervisorDecision(
                next_node="invalid_node",  # Invalid
                reasoning=""
            )
        )
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=mock_llm,
            registry=mock_registry
        )
        
        inputs = {"request": {}, "_internal": {"main_iteration": 0}}
        result = await supervisor.decide(inputs)
        
        # Should fall back to rule candidate
        assert result.next_node == "node1"

    async def test_llm_error_fallback(self, mock_registry, mock_llm):
        """Test fallback when LLM throws error."""
        mock_registry.evaluate_triggers.return_value = [(10, "node1")]
        mock_registry.build_llm_prompt.return_value = "Choose"
        
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            side_effect=RuntimeError("LLM error")
        )
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=mock_llm,
            registry=mock_registry
        )
        
        inputs = {"request": {}, "_internal": {"main_iteration": 0}}
        result = await supervisor.decide(inputs)
        
        # Should fall back to rule match
        assert result.next_node == "node1"

    async def test_child_decision_fallback(self, mock_registry):
        """Test child_decision fallback when no matches and no LLM."""
        mock_registry.evaluate_triggers.return_value = []
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=None,  # No LLM
            registry=mock_registry
        )
        
        inputs = {
            "request": {},
            "_internal": {
                "main_iteration": 0,
                "decision": "node1"  # Previous decision
            }
        }
        
        result = await supervisor.decide(inputs)
        
        # Should use child decision as fallback
        assert result.next_node == "node1"

    async def test_done_fallback_no_matches(self, mock_registry):
        """Test done fallback when no matches, no LLM, no child decision."""
        mock_registry.evaluate_triggers.return_value = []
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=None,
            registry=mock_registry
        )
        
        inputs = {
            "request": {},
            "_internal": {"main_iteration": 0}
        }
        
        result = await supervisor.decide(inputs)
        
        # Should return done
        assert result.next_node == "done"

    async def test_build_matched_rules_with_when_not(self, mock_registry, mock_llm):
        """Test _build_matched_rules with when_not condition."""
        contract_when_not = NodeContract(
            name="when_not_node",
            description="Node with when_not",
            reads=[],
            writes=[],
            supervisor="main",
            trigger_conditions=[
                TriggerCondition(when_not={"done": True}, priority=5)
            ]
        )
        mock_registry.get_contract.side_effect = lambda name: {
            "when_not_node": contract_when_not,
        }.get(name)
        mock_registry.evaluate_triggers.return_value = [(5, "when_not_node")]
        mock_registry.get_supervisor_nodes.return_value = ["when_not_node"]
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=None,
            registry=mock_registry
        )
        
        inputs = {"request": {}, "_internal": {"main_iteration": 0}}
        result = await supervisor.decide_with_trace(inputs)
        
        assert result.selected_node == "when_not_node"
        assert result.reason.decision_type == "rule_match"

    async def test_context_slices_collection(self, mock_registry):
        """Test that context slices are collected from base + candidate reads."""
        # Create contracts with different reads
        contract1 = NodeContract(
            name="node1",
            description="Node 1",
            reads=["request", "profile_card"],
            writes=["response"],
            supervisor="main",
            trigger_conditions=[
                TriggerCondition(when={"action": "analyze"}, priority=10)
            ]
        )
        
        contract2 = NodeContract(
            name="node2",
            description="Node 2",
            reads=["request", "interview"],
            writes=["response"],
            supervisor="main",
            trigger_conditions=[
                TriggerCondition(when={"action": "interview"}, priority=9)
            ]
        )
        
        mock_registry.get_contract.side_effect = lambda name: {
            "node1": contract1,
            "node2": contract2,
        }.get(name)
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=None,
            registry=mock_registry
        )
        
        # Test with node1 as candidate
        slices = supervisor._collect_context_slices(
            state={},
            rule_candidates=["node1"]
        )
        
        # Should include base slices + node1's reads
        expected = {"request", "response", "_internal", "profile_card"}
        assert slices == expected
        
        # Test with both nodes as candidates
        slices = supervisor._collect_context_slices(
            state={},
            rule_candidates=["node1", "node2"]
        )
        
        # Should include base slices + both nodes' reads
        expected = {"request", "response", "_internal", "profile_card", "interview"}
        assert slices == expected

    async def test_summarize_slice_dict(self, mock_registry):
        """Test slice summarization for dict data."""
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=None,
            registry=mock_registry
        )
        
        # Small dict
        small_dict = {"key1": "value1", "key2": "value2"}
        summary = supervisor._summarize_slice("test", small_dict)
        assert "test:" in summary
        assert "key1" in summary
        
        # Large dict (should be truncated)
        large_dict = {f"key{i}": f"value{i}" * 50 for i in range(20)}
        summary = supervisor._summarize_slice("test", large_dict)
        assert "test:" in summary
        assert "..." in summary or "key" in summary

    async def test_summarize_slice_list(self, mock_registry):
        """Test slice summarization for list data."""
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=None,
            registry=mock_registry
        )
        
        # Empty list
        summary = supervisor._summarize_slice("test", [])
        assert "test:" in summary
        assert "[]" in summary or "(empty)" in summary
        
        # Small list
        small_list = [1, 2, 3]
        summary = supervisor._summarize_slice("test", small_list)
        assert "test:" in summary
        
        # Large list (should show count)
        large_list = list(range(100))
        summary = supervisor._summarize_slice("test", large_list)
        assert "test:" in summary
        assert "items" in summary or "100" in summary

    async def test_summarize_slice_empty(self, mock_registry):
        """Test slice summarization for empty data."""
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=None,
            registry=mock_registry
        )
        
        summary = supervisor._summarize_slice("test", None)
        assert "test: (empty)" in summary
        
        summary = supervisor._summarize_slice("test", {})
        assert "test: (empty)" in summary

    async def test_llm_receives_enriched_context(self, mock_registry, mock_llm):
        """Test that LLM receives enriched context with candidate slices."""
        # Create contract with specific reads
        contract = NodeContract(
            name="analyzer",
            description="Analyzer node",
            reads=["request", "profile_card", "interview"],
            writes=["response"],
            supervisor="main",
            trigger_conditions=[
                TriggerCondition(when={"action": "analyze"}, priority=10)
            ]
        )
        
        mock_registry.get_contract.side_effect = lambda name: contract if name == "analyzer" else None
        mock_registry.evaluate_triggers.return_value = [(10, "analyzer")]
        # Use a callable that includes context in the prompt
        def build_prompt_with_context(supervisor, state, context=None):
            prompt = "Choose next action"
            if context:
                prompt += f"\n\n## Current Context\n{context}\n"
            return prompt
        mock_registry.build_llm_prompt.side_effect = build_prompt_with_context
        mock_registry.get_supervisor_nodes.return_value = ["analyzer"]
        
        from agent_contracts.supervisor import SupervisorDecision
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            return_value=SupervisorDecision(
                next_node="analyzer",
                reasoning="Analyzing user profile"
            )
        )
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=mock_llm,
            registry=mock_registry
        )
        
        state = {
            "request": {"action": "analyze", "message": "test"},
            "response": {"content": "previous response"},
            "_internal": {"main_iteration": 0},
            "profile_card": {"preferences": {"style": "casual"}},
            "interview": {"questions": []}
        }
        
        result = await supervisor.decide(state)
        
        # Verify LLM was called
        assert mock_llm.with_structured_output.return_value.ainvoke.called
        
        # Get the prompt that was passed to LLM
        call_args = mock_llm.with_structured_output.return_value.ainvoke.call_args
        prompt = call_args[0][0]
        
        # Verify enriched context includes candidate slices
        assert "request:" in prompt
        assert "profile_card:" in prompt
        assert "interview:" in prompt
        
        assert result.next_node == "analyzer"

