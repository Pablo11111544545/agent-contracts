"""Tests for runtime/state_ops module."""
import pytest

from agent_contracts.runtime.state_ops import (
    ensure_slices,
    merge_session,
    reset_internal_flags,
    create_base_state,
    copy_slice,
    update_slice,
    get_nested,
)
from agent_contracts.state_accessors import Internal, Request, Response


class TestEnsureSlices:
    """Tests for ensure_slices function."""

    def test_creates_missing_slices(self):
        """Creates slices that don't exist."""
        state = {}
        result = ensure_slices(state, ["request", "response", "_internal"])
        
        assert "request" in result
        assert "response" in result
        assert "_internal" in result
        assert result["request"] == {}

    def test_preserves_existing_slices(self):
        """Does not overwrite existing slices."""
        state = {"request": {"action": "test"}}
        result = ensure_slices(state, ["request", "response"])
        
        assert result["request"] == {"action": "test"}
        assert result["response"] == {}

    def test_replaces_non_dict_slices(self):
        """Replaces non-dict values with empty dicts."""
        state = {"request": "not a dict"}
        result = ensure_slices(state, ["request"])
        
        assert result["request"] == {}

    def test_is_immutable(self):
        """Does not mutate original state."""
        state = {}
        result = ensure_slices(state, ["test"])
        
        assert "test" not in state
        assert "test" in result


class TestMergeSession:
    """Tests for merge_session function."""

    def test_merges_session_data(self):
        """Merges session data into state."""
        state = {"interview": {"count": 1}}
        session = {"interview": {"history": ["q1"]}}
        
        result = merge_session(state, session, ["interview"])
        
        assert result["interview"]["count"] == 1
        assert result["interview"]["history"] == ["q1"]

    def test_default_slices(self):
        """Uses default slices when not specified (only _internal now)."""
        state = {}
        session = {
            "_internal": {"active_mode": "orders"},
            "workflow": {"data": "test"},
        }
        
        result = merge_session(state, session)
        
        # Default only merges _internal
        assert result["_internal"]["active_mode"] == "orders"
        # Other slices not merged by default
        assert "workflow" not in result

    def test_ignores_missing_session_slices(self):
        """Does not add slices that aren't in session data."""
        state = {}
        session = {"interview": {"data": "test"}}
        
        result = merge_session(state, session, ["interview", "shopping"])
        
        assert "interview" in result
        assert "shopping" not in result

    def test_handles_non_dict_session_slice(self):
        """Ignores non-dict session slice values."""
        state = {"interview": {"existing": "data"}}
        session = {"interview": "not a dict"}
        
        result = merge_session(state, session, ["interview"])
        
        # Should not be merged
        assert result["interview"] == {"existing": "data"}

    def test_is_immutable(self):
        """Does not mutate original state."""
        state = {"interview": {"count": 1}}
        session = {"interview": {"new": "data"}}
        
        result = merge_session(state, session, ["interview"])
        
        assert "new" not in state["interview"]
        assert "new" in result["interview"]


class TestResetInternalFlags:
    """Tests for reset_internal_flags function."""

    def test_reset_with_kwargs(self):
        """Resets flags using keyword arguments."""
        state = {"_internal": {"turn_count": 5, "is_first_turn": False}}
        
        result = reset_internal_flags(state, turn_count=0, is_first_turn=True)
        
        assert Internal.turn_count.get(result) == 0
        assert Internal.is_first_turn.get(result) is True

    def test_reset_with_dict(self):
        """Resets flags using dict."""
        state = {"_internal": {"error": "some error"}}
        
        result = reset_internal_flags(state, flags={"error": None})
        
        assert Internal.error.get(result) is None

    def test_ignores_unknown_flags(self):
        """Ignores flags that don't have accessors."""
        state = {}
        
        # Should not raise
        result = reset_internal_flags(state, unknown_flag="value", turn_count=0)
        
        assert Internal.turn_count.get(result) == 0

    def test_is_immutable(self):
        """Does not mutate original state."""
        state = {"_internal": {"turn_count": 5}}
        
        result = reset_internal_flags(state, turn_count=0)
        
        assert state["_internal"]["turn_count"] == 5
        assert result["_internal"]["turn_count"] == 0


class TestCreateBaseState:
    """Tests for create_base_state function."""

    def test_creates_minimal_state(self):
        """Creates state with minimal args."""
        state = create_base_state()
        
        assert Request.session_id.get(state) == ""
        assert Request.action.get(state) == ""
        assert Internal.turn_count.get(state) == 0
        assert Internal.is_first_turn.get(state) is True

    def test_creates_full_state(self):
        """Creates state with all args."""
        state = create_base_state(
            session_id="abc123",
            action="answer",
            params={"key": "value"},
            message="Hello",
            image="base64data",
            active_mode="shopping",
        )
        
        assert Request.session_id.get(state) == "abc123"
        assert Request.action.get(state) == "answer"
        assert Request.params.get(state) == {"key": "value"}
        assert Request.message.get(state) == "Hello"
        assert Request.image.get(state) == "base64data"
        assert Internal.active_mode.get(state) == "shopping"

    def test_response_is_cleared(self):
        """Response slice is initialized empty."""
        state = create_base_state()
        
        assert Response.response_type.get(state) is None
        assert Response.response_data.get(state) is None

    def test_internal_flags_initialized(self):
        """Internal flags are properly initialized."""
        state = create_base_state()
        
        assert Internal.next_node.get(state) is None
        assert Internal.decision.get(state) is None
        assert Internal.error.get(state) is None


class TestCopySlice:
    """Tests for copy_slice function."""

    def test_copies_existing_slice(self):
        """Copies slice that exists."""
        state = {"interview": {"count": 1, "data": "test"}}
        
        result = copy_slice(state, "interview")
        
        assert result == {"count": 1, "data": "test"}
        # Verify it's a copy
        result["count"] = 99
        assert state["interview"]["count"] == 1

    def test_returns_empty_for_missing(self):
        """Returns empty dict for missing slice."""
        state = {}
        result = copy_slice(state, "interview")
        assert result == {}

    def test_returns_empty_for_non_dict(self):
        """Returns empty dict for non-dict slice."""
        state = {"interview": "not a dict"}
        result = copy_slice(state, "interview")
        assert result == {}


class TestUpdateSlice:
    """Tests for update_slice function."""

    def test_updates_existing_slice(self):
        """Updates fields in existing slice."""
        state = {"interview": {"count": 1}}
        
        result = update_slice(state, "interview", count=2, new_field="value")
        
        assert result["interview"]["count"] == 2
        assert result["interview"]["new_field"] == "value"

    def test_creates_slice_if_missing(self):
        """Creates slice if it doesn't exist."""
        state = {}
        
        result = update_slice(state, "interview", count=1)
        
        assert result["interview"]["count"] == 1

    def test_is_immutable(self):
        """Does not mutate original state."""
        state = {"interview": {"count": 1}}
        
        result = update_slice(state, "interview", count=2)
        
        assert state["interview"]["count"] == 1
        assert result["interview"]["count"] == 2


class TestGetNested:
    """Tests for get_nested function."""

    def test_gets_nested_value(self):
        """Gets value at nested path."""
        state = {"interview": {"collected_info": {"name": "Alice"}}}
        
        result = get_nested(state, "interview", "collected_info", "name")
        
        assert result == "Alice"

    def test_returns_default_for_missing(self):
        """Returns default for missing path."""
        state = {}
        
        result = get_nested(state, "interview", "missing", default="unknown")
        
        assert result == "unknown"

    def test_returns_none_by_default(self):
        """Returns None when no default specified."""
        state = {}
        
        result = get_nested(state, "missing", "path")
        
        assert result is None

    def test_handles_non_dict_in_path(self):
        """Handles non-dict value in path."""
        state = {"interview": "not a dict"}
        
        result = get_nested(state, "interview", "field", default="fallback")
        
        assert result == "fallback"

    def test_single_level(self):
        """Works with single key."""
        state = {"interview": {"data": "test"}}
        
        result = get_nested(state, "interview")
        
        assert result == {"data": "test"}
