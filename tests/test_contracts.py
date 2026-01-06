import pytest
from pydantic import ValidationError
from agent_contracts import NodeContract, TriggerCondition

class TestNodeContract:
    def test_valid_contract(self):
        """Test creating a valid NodeContract."""
        contract = NodeContract(
            name="test_node",
            description="A test node",
            reads=["input_slice"],
            writes=["output_slice"],
            supervisor="main_supervisor"
        )
        assert contract.name == "test_node"
        assert contract.reads == ["input_slice"]
        assert contract.writes == ["output_slice"]
        assert contract.supervisor == "main_supervisor"
        assert contract.requires_llm is False
        assert contract.is_terminal is False

    def test_missing_required_fields(self):
        """Test that missing required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            NodeContract(
                name="test_node",
                # description is missing
                reads=[],
                writes=[],
            )

    def test_trigger_condition_defaults(self):
        """Test default values for TriggerCondition."""
        condition = TriggerCondition()
        assert condition.priority == 0
        assert condition.when is None
        assert condition.when_not is None
        assert condition.llm_hint is None

    def test_contract_with_triggers(self):
        """Test contract with trigger conditions."""
        condition = TriggerCondition(
            when={"status": "active"},
            priority=5
        )
        contract = NodeContract(
            name="triggered_node",
            description="Node with triggers",
            reads=[],
            writes=[],
            supervisor="test_supervisor",
            trigger_conditions=[condition]
        )
        assert len(contract.trigger_conditions) == 1
        assert contract.trigger_conditions[0].priority == 5
        assert contract.trigger_conditions[0].when == {"status": "active"}
