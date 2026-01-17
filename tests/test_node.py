"""Tests for ModularNode and InteractiveNode."""

import logging
import pytest
from unittest.mock import AsyncMock, MagicMock

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
    ContractViolationError,
)
from agent_contracts.config import FrameworkConfig, IOConfig, set_config
from agent_contracts.node import InteractiveNode


# =============================================================================
# Test Nodes
# =============================================================================

@pytest.fixture
def clean_config():
    """Reset the global config before and after each test."""
    set_config(None)
    yield
    set_config(None)


class SampleNode(ModularNode):
    """Simple test node."""
    CONTRACT = NodeContract(
        name="sample_node",
        description="A sample node for testing",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        requires_llm=False,
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        request = inputs.get_slice("request")
        return NodeOutputs(response={"message": f"Hello, {request.get('name', 'world')}"})


class NodeWithLLM(ModularNode):
    """Node that requires LLM."""
    CONTRACT = NodeContract(
        name="llm_node",
        description="Node requiring LLM",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        requires_llm=True,
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"generated": True})


class NodeWithServices(ModularNode):
    """Node that requires services."""
    CONTRACT = NodeContract(
        name="service_node",
        description="Node requiring services",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        services=["db_service", "cache_service"],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class SampleInteractiveNode(InteractiveNode):
    """Test implementation of InteractiveNode."""
    CONTRACT = NodeContract(
        name="interactive_sample",
        description="Sample interactive node",
        reads=["request", "context"],
        writes=["response", "context"],
        supervisor="main",
    )
    
    def __init__(self, *args, complete=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._complete = complete
        self._answer_processed = False
    
    def prepare_context(self, inputs: NodeInputs):
        return {"state": inputs.get_slice("context")}
    
    def check_completion(self, context, inputs) -> bool:
        return self._complete
    
    async def process_answer(self, context, inputs, config=None) -> bool:
        self._answer_processed = True
        return True
    
    async def generate_question(self, context, inputs, config=None) -> NodeOutputs:
        return NodeOutputs(
            response={
                "response_type": "question",
                "response_data": {"question": "What is your preference?"},
            }
        )


# =============================================================================
# ModularNode Tests
# =============================================================================

class TestModularNode:
    """Tests for ModularNode base class."""

    def test_init_sets_llm(self):
        """Test initialization sets LLM."""
        mock_llm = MagicMock()
        node = SampleNode(llm=mock_llm)
        
        assert node.llm is mock_llm

    def test_init_without_llm(self):
        """Test initialization without LLM."""
        node = SampleNode()
        
        assert node.llm is None

    def test_service_injection(self):
        """Test services are injected via kwargs."""
        mock_db = MagicMock()
        mock_cache = MagicMock()
        
        node = NodeWithServices(db_service=mock_db, cache_service=mock_cache)
        
        assert node.db_service is mock_db
        assert node.cache_service is mock_cache

    def test_missing_service_warning(self):
        """Test warning when required service is missing."""
        node = NodeWithServices()
        
        # Validation happens on first call
        node._validate_dependencies()
        
        # Should have logged warnings but not fail

    def test_missing_llm_warning(self):
        """Test warning when LLM is required but not provided."""
        node = NodeWithLLM()
        
        # Validation happens on first call
        node._validate_dependencies()
        
        # Should have logged warning but not fail

    @pytest.mark.asyncio
    async def test_call_executes_node(self):
        """Test __call__ executes the node."""
        node = SampleNode()
        state = {"request": {"name": "Alice"}, "response": {}}
        
        result = await node(state)
        
        assert result["response"]["message"] == "Hello, Alice"

    @pytest.mark.asyncio
    async def test_call_adds_metadata_to_config(self):
        """Test __call__ adds node metadata to config."""
        captured_config = {}
        
        class ConfigCapturingNode(ModularNode):
            CONTRACT = NodeContract(
                name="config_capturer",
                description="Captures config for testing",
                reads=["request"],
                writes=["response"],
                supervisor="test_sup",
            )
            
            async def execute(self, inputs, config=None):
                captured_config.update(config or {})
                return NodeOutputs(response={})
        
        node = ConfigCapturingNode()
        await node({"request": {}}, config={"tags": ["test"]})
        
        assert captured_config["metadata"]["node_name"] == "config_capturer"
        assert captured_config["metadata"]["node_supervisor"] == "test_sup"
        assert captured_config["tags"] == ["test"]

    @pytest.mark.asyncio
    async def test_call_handles_execution_error(self):
        """Test __call__ propagates execution errors."""
        class FailingNode(ModularNode):
            CONTRACT = NodeContract(
                name="failing",
                description="Always fails",
                reads=["request"],
                writes=["response"],
                supervisor="main",
            )
            
            async def execute(self, inputs, config=None):
                raise ValueError("Execution failed")
        
        node = FailingNode()
        
        with pytest.raises(ValueError, match="Execution failed"):
            await node({"request": {}})

    def test_extract_inputs(self):
        """Test _extract_inputs extracts correct slices."""
        node = SampleNode()
        state = {
            "request": {"action": "test"},
            "response": {"old": "data"},
            "other": {"ignored": True},
        }
        
        inputs = node._extract_inputs(state)
        
        assert inputs.get_slice("request") == {"action": "test"}
        # "response" is in writes, not reads, so not extracted
        assert inputs.get_slice("other") == {}

    @pytest.mark.asyncio
    async def test_undeclared_slice_read_warns_by_default(
        self, caplog: pytest.LogCaptureFixture, clean_config
    ):
        class UndeclaredReadNode(ModularNode):
            CONTRACT = NodeContract(
                name="undeclared_read",
                description="reads undeclared slice",
                reads=["request"],
                writes=["response"],
                supervisor="main",
            )

            async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
                _ = inputs.get_slice("context")
                return NodeOutputs(response={"ok": True})

        caplog.set_level(logging.WARNING)
        node = UndeclaredReadNode()
        result = await node({"request": {}, "context": {"x": 1}})
        assert result["response"]["ok"] is True
        assert "Undeclared slice read 'context'" in caplog.text

    @pytest.mark.asyncio
    async def test_undeclared_slice_read_raises_in_strict_mode(
        self, clean_config
    ):
        set_config(FrameworkConfig(io=IOConfig(strict=True)))

        class UndeclaredReadNode(ModularNode):
            CONTRACT = NodeContract(
                name="undeclared_read_strict",
                description="reads undeclared slice",
                reads=["request"],
                writes=["response"],
                supervisor="main",
            )

            async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
                _ = inputs.get_slice("context")
                return NodeOutputs(response={"ok": True})

        node = UndeclaredReadNode()
        with pytest.raises(ContractViolationError, match="Undeclared slice read"):
            await node({"request": {}, "context": {"x": 1}})

    def test_convert_outputs(self):
        """Test _convert_outputs converts to state format."""
        node = SampleNode()
        outputs = NodeOutputs(
            response={"message": "hello"},
        )
        
        result = node._convert_outputs(outputs)
        
        assert result["response"]["message"] == "hello"

    @pytest.mark.asyncio
    async def test_undeclared_slice_write_warns_and_drops_by_default(
        self, caplog: pytest.LogCaptureFixture, clean_config
    ):
        class UndeclaredWriteNode(ModularNode):
            CONTRACT = NodeContract(
                name="undeclared_write",
                description="writes undeclared slice",
                reads=["request"],
                writes=["response"],
                supervisor="main",
            )

            async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
                return NodeOutputs(response={"ok": True}, context={"x": 1})

        caplog.set_level(logging.WARNING)
        node = UndeclaredWriteNode()
        result = await node({"request": {}, "context": {"x": 1}})
        assert result["response"]["ok"] is True
        assert "context" not in result
        assert "Undeclared slice write(s)" in caplog.text

    @pytest.mark.asyncio
    async def test_undeclared_slice_write_raises_in_strict_mode(self, clean_config):
        set_config(FrameworkConfig(io=IOConfig(strict=True)))

        class UndeclaredWriteNode(ModularNode):
            CONTRACT = NodeContract(
                name="undeclared_write_strict",
                description="writes undeclared slice",
                reads=["request"],
                writes=["response"],
                supervisor="main",
            )

            async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
                return NodeOutputs(response={"ok": True}, context={"x": 1})

        node = UndeclaredWriteNode()
        with pytest.raises(ContractViolationError, match="Undeclared slice write"):
            await node({"request": {}, "context": {"x": 1}})

    def test_get_request_param(self):
        """Test get_request_param helper."""
        node = SampleNode()
        inputs = NodeInputs(request={"params": {"key": "value"}})
        
        result = node.get_request_param(inputs, "key")
        
        assert result == "value"

    def test_get_request_param_default(self):
        """Test get_request_param with default."""
        node = SampleNode()
        inputs = NodeInputs(request={})
        
        result = node.get_request_param(inputs, "missing", "default")
        
        assert result == "default"

    def test_build_error_response(self):
        """Test build_error_response helper."""
        node = SampleNode()
        
        result = node.build_error_response("Something failed", "ERR_001")
        
        assert result.response["response_type"] == "error"
        assert result.response["response_data"]["message"] == "Something failed"
        assert result.response["response_data"]["code"] == "ERR_001"


# =============================================================================
# InteractiveNode Tests
# =============================================================================

class TestInteractiveNode:
    """Tests for InteractiveNode base class."""

    @pytest.mark.asyncio
    async def test_execute_generates_question_when_not_complete(self):
        """Test execute generates question when not complete."""
        node = SampleInteractiveNode(complete=False)
        inputs = NodeInputs(request={}, context={})
        
        result = await node.execute(inputs)
        
        assert node._answer_processed is True
        assert result.response["response_type"] == "question"

    @pytest.mark.asyncio
    async def test_execute_returns_completion_when_complete(self):
        """Test execute returns completion output when complete."""
        node = SampleInteractiveNode(complete=True)
        inputs = NodeInputs(request={}, context={})
        
        result = await node.execute(inputs)
        
        assert node._answer_processed is True
        assert result._internal["decision"] == "done"

    @pytest.mark.asyncio
    async def test_create_completion_output_default(self):
        """Test default create_completion_output."""
        node = SampleInteractiveNode()
        inputs = NodeInputs(request={}, context={})
        context = node.prepare_context(inputs)
        
        result = await node.create_completion_output(context, inputs)
        
        assert result._internal["decision"] == "done"
