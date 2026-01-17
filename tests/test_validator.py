"""Tests for ContractValidator."""
import pytest

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
)
from agent_contracts.registry import NodeRegistry
from agent_contracts.validator import ContractValidator, ValidationResult


# =============================================================================
# Test Fixtures
# =============================================================================

class ValidNode(ModularNode):
    """A valid node for testing."""
    CONTRACT = NodeContract(
        name="valid_node",
        description="A valid test node",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=10,
                when={"request.action": "test"},
                llm_hint="Test action",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class AnotherValidNode(ModularNode):
    """Another valid node that also writes to response."""
    CONTRACT = NodeContract(
        name="another_valid_node",
        description="Another valid test node",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=5,
                when={"request.action": "other"},
                llm_hint="Other action",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class NodeWithUnknownSlice(ModularNode):
    """A node with an unknown slice."""
    CONTRACT = NodeContract(
        name="unknown_slice_node",
        description="Node with unknown slice",
        reads=["invalid_slice"],  # This slice doesn't exist
        writes=["response"],
        supervisor="main",
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class NodeWithUnknownService(ModularNode):
    """A node requiring an unknown service."""
    CONTRACT = NodeContract(
        name="unknown_service_node",
        description="Node with unknown service",
        reads=["request"],
        writes=["response"],
        services=["nonexistent_service"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(priority=1)
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class OrphanNode(ModularNode):
    """A node without a supervisor."""
    CONTRACT = NodeContract(
        name="orphan_node",
        description="Node without supervisor",
        reads=["request"],
        writes=["response"],
        supervisor="",  # Empty supervisor
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class UnreachableNode(ModularNode):
    """A node with no trigger conditions."""
    CONTRACT = NodeContract(
        name="unreachable_node",
        description="Node without trigger conditions",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[],  # No conditions
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class RequestWriterNode(ModularNode):
    """A node that writes to request slice."""
    CONTRACT = NodeContract(
        name="request_writer",
        description="Writes to request slice",
        reads=["request"],
        writes=["request"],
        supervisor="main",
        trigger_conditions=[TriggerCondition(priority=1)],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(request={"mutated": True})


# =============================================================================
# Tests
# =============================================================================

class TestValidationResult:
    """Tests for ValidationResult."""
    
    def test_empty_result_is_valid(self):
        """Empty result should be valid."""
        result = ValidationResult()
        assert result.is_valid
        assert not result.has_errors
        assert not result.has_warnings
    
    def test_result_with_errors_is_invalid(self):
        """Result with errors should be invalid."""
        result = ValidationResult(errors=["Some error"])
        assert not result.is_valid
        assert result.has_errors
    
    def test_result_with_warnings_is_valid(self):
        """Result with only warnings should be valid."""
        result = ValidationResult(warnings=["Some warning"])
        assert result.is_valid
        assert not result.has_errors
        assert result.has_warnings
    
    def test_str_format(self):
        """Test string formatting."""
        result = ValidationResult(
            errors=["Error 1"],
            warnings=["Warning 1"],
            info=["Info 1"],
        )
        output = str(result)
        assert "ERRORS:" in output
        assert "Error 1" in output
        assert "WARNINGS:" in output
        assert "Warning 1" in output
        assert "INFO:" in output
        assert "Info 1" in output


class TestContractValidator:
    """Tests for ContractValidator."""
    
    def test_valid_nodes_pass_validation(self):
        """Valid nodes should pass validation."""
        registry = NodeRegistry()
        registry.register(ValidNode)
        registry.register(AnotherValidNode)
        
        validator = ContractValidator(registry)
        result = validator.validate()
        
        assert result.is_valid
        assert not result.has_errors
    
    def test_unknown_slice_detected(self):
        """Unknown slice should be detected as error."""
        registry = NodeRegistry()
        # Suppress the warning during registration
        registry.register(NodeWithUnknownSlice)
        
        validator = ContractValidator(registry)
        result = validator.validate()
        
        assert result.has_errors
        assert any("invalid_slice" in e for e in result.errors)
        assert any("unknown_slice_node" in e for e in result.errors)
    
    def test_unknown_service_warning(self):
        """Unknown service should be detected as warning."""
        registry = NodeRegistry()
        registry.register(NodeWithUnknownService)
        
        # Provide known services
        validator = ContractValidator(
            registry,
            known_services={"db_service", "api_service"},
        )
        result = validator.validate()
        
        assert result.has_warnings
        assert any("nonexistent_service" in w for w in result.warnings)
    
    def test_service_validation_skipped_if_no_known_services(self):
        """Service validation should be skipped if known_services is None."""
        registry = NodeRegistry()
        registry.register(NodeWithUnknownService)
        
        # No known_services provided
        validator = ContractValidator(registry)
        result = validator.validate()
        
        # Should not have service-related warnings
        assert not any("nonexistent_service" in w for w in result.warnings)
    
    def test_orphan_node_warning(self):
        """Orphan node should be detected as warning."""
        registry = NodeRegistry()
        registry.register(OrphanNode)
        
        validator = ContractValidator(registry)
        result = validator.validate()
        
        assert result.has_warnings
        assert any("orphan" in w.lower() for w in result.warnings)
    
    def test_unreachable_node_warning(self):
        """Unreachable node should be detected as warning."""
        registry = NodeRegistry()
        registry.register(UnreachableNode)
        
        validator = ContractValidator(registry)
        result = validator.validate()
        
        assert result.has_warnings
        assert any("unreachable" in w.lower() for w in result.warnings)
    
    def test_shared_writers_info(self):
        """Shared writers should be reported as info."""
        registry = NodeRegistry()
        registry.register(ValidNode)
        registry.register(AnotherValidNode)
        
        validator = ContractValidator(registry)
        result = validator.validate()
        
        # Both nodes write to 'response'
        assert any("response" in info and "valid_node" in info for info in result.info)

    def test_request_write_warning(self):
        """Writing to request slice should be warned."""
        registry = NodeRegistry()
        registry.register(RequestWriterNode)
        
        validator = ContractValidator(registry)
        result = validator.validate()
        
        assert result.has_warnings
        assert any("request" in w for w in result.warnings)

    def test_strict_mode_escalates_warnings(self):
        """Strict mode should convert warnings to errors."""
        registry = NodeRegistry()
        registry.register(NodeWithUnknownService)
        
        validator = ContractValidator(
            registry,
            known_services={"db_service"},
            strict=True,
        )
        result = validator.validate()
        
        assert result.has_errors
        assert not result.has_warnings
        assert any("STRICT:" in e for e in result.errors)
    
    def test_get_shared_writers(self):
        """get_shared_writers should return correct mapping."""
        registry = NodeRegistry()
        registry.register(ValidNode)
        registry.register(AnotherValidNode)
        
        validator = ContractValidator(registry)
        writers = validator.get_shared_writers()
        
        assert "response" in writers
        assert set(writers["response"]) == {"valid_node", "another_valid_node"}
    
    def test_get_slice_readers(self):
        """get_slice_readers should return correct mapping."""
        registry = NodeRegistry()
        registry.register(ValidNode)
        registry.register(AnotherValidNode)
        
        validator = ContractValidator(registry)
        readers = validator.get_slice_readers()
        
        assert "request" in readers
        assert set(readers["request"]) == {"valid_node", "another_valid_node"}

    def test_all_pass_message(self):
        """Test validation result str when all validations pass."""
        result = ValidationResult()
        output = str(result)
        assert "All validations passed" in output

    def test_get_unused_slices_write_only(self):
        """get_unused_slices detects write-only slices."""
        class WriteOnlyNode(ModularNode):
            CONTRACT = NodeContract(
                name="write_only_node",
                description="Writes to custom slice",
                reads=["request"],
                writes=["custom_output"],
                supervisor="main",
                trigger_conditions=[TriggerCondition(priority=10)],
            )
            async def execute(self, inputs, config=None): 
                return NodeOutputs()
        
        registry = NodeRegistry()
        registry.add_valid_slice("custom_output")
        registry.register(WriteOnlyNode)
        
        validator = ContractValidator(registry)
        unused = validator.get_unused_slices()
        
        assert "custom_output" in unused
        assert unused["custom_output"] == "write_only"

    def test_get_unused_slices_read_only(self):
        """get_unused_slices detects read-only slices (non-request)."""
        class ReadOnlyNode(ModularNode):
            CONTRACT = NodeContract(
                name="read_only_node",
                description="Reads from custom slice",
                reads=["custom_input"],
                writes=["response"],
                supervisor="main",
                trigger_conditions=[TriggerCondition(priority=10)],
            )
            async def execute(self, inputs, config=None): 
                return NodeOutputs()
        
        registry = NodeRegistry()
        registry.add_valid_slice("custom_input")
        registry.register(ReadOnlyNode)
        
        validator = ContractValidator(registry)
        unused = validator.get_unused_slices()
        
        # custom_input is read but never written
        assert "custom_input" in unused
        assert unused["custom_input"] == "read_only"

    def test_get_unused_slices_request_not_flagged(self):
        """get_unused_slices doesn't flag 'request' as read-only."""
        registry = NodeRegistry()
        registry.register(ValidNode)  # Reads from request, writes to response
        
        validator = ContractValidator(registry)
        unused = validator.get_unused_slices()
        
        # request should NOT be flagged as read_only (it's an input slice)
        assert "request" not in unused
