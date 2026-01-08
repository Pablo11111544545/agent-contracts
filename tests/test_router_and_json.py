"""Tests for router and JSON utilities."""

import pytest
from datetime import datetime

from agent_contracts.router import BaseActionRouter
from agent_contracts.utils.json import json_serializer, json_dumps


# =============================================================================
# Router Tests
# =============================================================================

class SampleRouter(BaseActionRouter):
    """Test implementation of BaseActionRouter."""
    
    def route(self, action: str, state: dict | None = None) -> str:
        if action == "create":
            return "create_supervisor"
        elif action == "search":
            return "search_supervisor"
        elif action == "unknown":
            raise ValueError(f"Unknown action: {action}")
        return "default_supervisor"


class TestBaseActionRouter:
    """Tests for BaseActionRouter."""

    @pytest.fixture
    def router(self):
        return SampleRouter()

    def test_route_returns_correct_target(self, router):
        """Test route method returns correct target."""
        assert router.route("create") == "create_supervisor"
        assert router.route("search") == "search_supervisor"
        assert router.route("other") == "default_supervisor"

    def test_route_raises_for_unknown_action(self, router):
        """Test route raises ValueError for unknown action."""
        with pytest.raises(ValueError, match="Unknown action"):
            router.route("unknown")

    def test_call_updates_state_with_next_node(self, router):
        """Test __call__ updates state with next_node."""
        state = {"request": {"action": "create"}}
        
        result = router(state)
        
        assert result["_internal"]["next_node"] == "create_supervisor"

    def test_call_handles_error(self, router):
        """Test __call__ handles routing errors gracefully."""
        state = {"request": {"action": "unknown"}}
        
        result = router(state)
        
        assert result["_internal"]["next_node"] is None
        assert "error" in result["_internal"]
        assert result["response"]["response_type"] == "error"
        assert result["response"]["response_data"]["code"] == "UNKNOWN_ACTION"

    def test_call_with_empty_request(self, router):
        """Test __call__ with empty request defaults to empty action."""
        state = {}
        
        result = router(state)
        
        # Empty action goes to default_supervisor
        assert result["_internal"]["next_node"] == "default_supervisor"


# =============================================================================
# JSON Utility Tests
# =============================================================================

class TestJsonSerializer:
    """Tests for json_serializer function."""

    def test_serializes_datetime(self):
        """Test serializing datetime to ISO format."""
        dt = datetime(2025, 1, 15, 12, 30, 45)
        
        result = json_serializer(dt)
        
        assert result == "2025-01-15T12:30:45"

    def test_raises_for_non_serializable(self):
        """Test raises TypeError for non-serializable objects."""
        class CustomObj:
            pass
        
        with pytest.raises(TypeError, match="is not JSON serializable"):
            json_serializer(CustomObj())


class TestJsonDumps:
    """Tests for json_dumps function."""

    def test_dumps_basic_dict(self):
        """Test basic dict serialization."""
        data = {"name": "Alice", "age": 30}
        
        result = json_dumps(data)
        
        assert '"name": "Alice"' in result
        assert '"age": 30' in result

    def test_dumps_with_datetime(self):
        """Test serialization with datetime."""
        data = {"created_at": datetime(2025, 1, 15, 12, 30, 45)}
        
        result = json_dumps(data)
        
        assert "2025-01-15T12:30:45" in result

    def test_dumps_preserves_unicode(self):
        """Test that unicode is preserved (ensure_ascii=False)."""
        data = {"name": "日本語"}
        
        result = json_dumps(data)
        
        assert "日本語" in result  # Not escaped

    def test_dumps_with_custom_kwargs(self):
        """Test that custom kwargs are passed through."""
        data = {"a": 1}
        
        result = json_dumps(data, indent=2)
        
        assert "\n" in result  # Indented output has newlines
