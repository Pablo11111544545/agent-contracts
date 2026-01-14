import pytest
from unittest.mock import MagicMock, AsyncMock
from agent_contracts import GenericSupervisor, NodeContract, TriggerCondition, TriggerMatch

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
        mock_registry.evaluate_triggers.return_value = [
            TriggerMatch(priority=10, node_name="node1", condition_index=0)
        ]
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
            TriggerMatch(priority=10, node_name="node1", condition_index=0),
            TriggerMatch(priority=10, node_name="node2", condition_index=0),
            TriggerMatch(priority=10, node_name="node3", condition_index=0),
            TriggerMatch(priority=10, node_name="node4", condition_index=0),
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
        mock_registry.evaluate_triggers.return_value = [
            TriggerMatch(priority=10, node_name="node1", condition_index=0)
        ]
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
        mock_registry.evaluate_triggers.return_value = [
            TriggerMatch(priority=10, node_name="node1", condition_index=0)
        ]
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
        mock_registry.evaluate_triggers.return_value = [
            TriggerMatch(priority=5, node_name="when_not_node", condition_index=0)
        ]
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
        slices, additional_context = supervisor._collect_context_slices(
            state={},
            rule_candidates=["node1"]
        )
        
        # Should include minimal slices (request, response, _internal)
        # Candidate node reads are not included as they're already evaluated in triggers
        expected = {"request", "response", "_internal"}
        assert slices == expected
        assert additional_context == ""
        
        # Test with both nodes as candidates
        slices, additional_context = supervisor._collect_context_slices(
            state={},
            rule_candidates=["node1", "node2"]
        )
        
        # Should still only include minimal slices regardless of candidates
        expected = {"request", "response", "_internal"}
        assert slices == expected
        assert additional_context == ""


    async def test_llm_receives_minimal_context(self, mock_registry, mock_llm):
        """Test that LLM receives minimal context (request + response + _internal).
        
        Candidate node reads are not included as they're already evaluated in triggers.
        This reduces token usage while maintaining conversation context.
        """
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
        mock_registry.evaluate_triggers.return_value = [
            TriggerMatch(priority=10, node_name="analyzer", condition_index=0)
        ]
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
        
        # Verify minimal context includes request, response, and _internal
        assert "request:" in prompt
        assert "response:" in prompt
        assert "_internal:" in prompt
        # These should NOT be included (already evaluated in triggers)
        assert "profile_card:" not in prompt
        assert "interview:" not in prompt
        
        assert result.next_node == "analyzer"


class TestSanitizeForLLM:
    """Tests for _sanitize_for_llm method using sanitize_for_llm_util."""
    
    def test_sanitize_image_data_png(self):
        """Test PNG base64 image detection and replacement."""
        supervisor = GenericSupervisor("test")
        
        # PNG base64 - long enough to be detected
        png_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" * 200
        result = supervisor._sanitize_for_llm(png_data, max_str_length=100)
        # New implementation may truncate or detect as base64
        assert "[TRUNCATED:" in result or "[BASE64_DATA" in result
    
    def test_sanitize_image_data_jpeg(self):
        """Test JPEG base64 image detection with MIME type."""
        supervisor = GenericSupervisor("test")
        
        # JPEG base64 - detects magic number
        jpeg_data = "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/" * 200
        result = supervisor._sanitize_for_llm(jpeg_data, max_str_length=100)
        # New implementation detects JPEG with MIME type
        assert result == "[BASE64_DATA:image/jpeg]"
    
    def test_sanitize_image_data_gif(self):
        """Test GIF base64 image detection with MIME type."""
        supervisor = GenericSupervisor("test")
        
        # GIF base64 - detects magic number
        gif_data = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" * 200
        result = supervisor._sanitize_for_llm(gif_data, max_str_length=100)
        # New implementation detects GIF with MIME type
        assert result == "[BASE64_DATA:image/gif]"
    
    def test_sanitize_image_data_uri(self):
        """Test data URI detection."""
        supervisor = GenericSupervisor("test")
        
        # Proper data URI format - needs data: prefix
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        result = supervisor._sanitize_for_llm(data_uri, max_str_length=100)
        # New implementation detects Data URI with MIME
        assert result == "[DATA_URI:image/png]"
    
    def test_sanitize_image_prefix(self):
        """Test string starting with 'image' without data: prefix."""
        supervisor = GenericSupervisor("test")
        
        # Without  prefix, treated as long text
        image_prefix = "image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" * 200
        result = supervisor._sanitize_for_llm(image_prefix, max_str_length=100)
        # Truncated as long text
        assert "[TRUNCATED:" in result
    
    def test_sanitize_long_text_truncation(self):
        """Test long text truncation."""
        supervisor = GenericSupervisor("test")
        
        # Use non-base64 characters to avoid base64 detection
        long_text = "hello world! " * 20  # 260 chars
        result = supervisor._sanitize_for_llm(long_text, max_str_length=100)
        
        # Should be truncated
        assert "[TRUNCATED:" in result
        assert len(result) < len(long_text)
    
    def test_sanitize_short_text_preserved(self):
        """Test that short text is preserved as-is."""
        supervisor = GenericSupervisor("test")
        
        short_text = "This is a short text"
        assert supervisor._sanitize_for_llm(short_text, max_str_length=10000) == short_text
    
    def test_sanitize_dict_recursive(self):
        """Test recursive sanitization in dict."""
        supervisor = GenericSupervisor("test")
        
        data = {
            "short": "short text",
            "long": "hello world! " * 20,  # Has spaces, won't be detected as base64
            "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" * 10,
            "nested": {
                "inner_long": "hello world! " * 20,  # Has spaces, won't be detected as base64
                "inner_short": "ok"
            }
        }
        
        result = supervisor._sanitize_for_llm(data, max_str_length=100)
        
        # Short text preserved
        assert result["short"] == "short text"
        # Long text with spaces truncated (not base64)
        assert "[TRUNCATED:" in result["long"]
        # Image data: 960 chars, no spaces, should be detected as base64 or truncated
        assert "[BASE64_DATA" in result["image"] or "[TRUNCATED:" in result["image"]
        # Nested dict: text with spaces is truncated (not base64)
        assert "[TRUNCATED:" in result["nested"]["inner_long"]
        assert result["nested"]["inner_short"] == "ok"
    
    def test_sanitize_list_recursive(self):
        """Test recursive sanitization in list."""
        supervisor = GenericSupervisor("test")
        
        data = [
            "short",
            "hello world! " * 20,  # Has spaces, won't be detected as base64
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" * 10,
            {"nested": "hello world! " * 20}  # Has spaces, won't be detected as base64
        ]
        
        result = supervisor._sanitize_for_llm(data, max_str_length=100)
        
        assert result[0] == "short"
        # Text with spaces is truncated (not base64)
        assert "[TRUNCATED:" in result[1]
        # 960 chars base64, no spaces, should be detected or truncated
        assert "[BASE64_DATA" in result[2] or "[TRUNCATED:" in result[2]
        # Text with spaces is truncated (not base64)
        assert "[TRUNCATED:" in result[3]["nested"]
    
    def test_sanitize_nested_structure(self):
        """Test sanitization in deeply nested structures."""
        supervisor = GenericSupervisor("test")
        
        data = {
            "level1": {
                "level2": {
                    "level3": [
                        {"text": "hello world! " * 20},  # Has spaces, won't be base64
                        {"image": "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/"}
                    ]
                }
            }
        }
        
        result = supervisor._sanitize_for_llm(data, max_str_length=100)
        
        # Deep nested text with spaces is truncated (not base64)
        assert "[TRUNCATED:" in result["level1"]["level2"]["level3"][0]["text"]
        # Deep nested image: 120 chars, no spaces, but not long enough for base64 detection (needs 128+)
        # Will be truncated instead
        assert "[TRUNCATED:" in result["level1"]["level2"]["level3"][1]["image"]
    
    def test_sanitize_non_string_types(self):
        """Test that non-string types are preserved."""
        supervisor = GenericSupervisor("test")
        
        # Numbers
        assert supervisor._sanitize_for_llm(123, max_str_length=100) == 123
        assert supervisor._sanitize_for_llm(45.67, max_str_length=100) == 45.67
        
        # Booleans
        assert supervisor._sanitize_for_llm(True, max_str_length=100) is True
        assert supervisor._sanitize_for_llm(False, max_str_length=100) is False
        
        # None
        assert supervisor._sanitize_for_llm(None, max_str_length=100) is None
    
    def test_sanitize_empty_structures(self):
        """Test sanitization of empty structures."""
        supervisor = GenericSupervisor("test")
        
        assert supervisor._sanitize_for_llm({}, max_str_length=100) == {}
        assert supervisor._sanitize_for_llm([], max_str_length=100) == []
        assert supervisor._sanitize_for_llm("", max_str_length=100) == ""
