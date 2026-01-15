"""Tests for runtime module."""
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

from agent_contracts.runtime import (
    RequestContext,
    ExecutionResult,
    RuntimeHooks,
    DefaultHooks,
    SessionStore,
    InMemorySessionStore,
    AgentRuntime,
)
from agent_contracts.state_accessors import Internal, Request, Response


class TestRequestContext:
    """Tests for RequestContext dataclass."""

    def test_basic_creation(self):
        """Basic context creation works."""
        ctx = RequestContext(
            session_id="abc123",
            action="answer",
        )
        assert ctx.session_id == "abc123"
        assert ctx.action == "answer"
        assert ctx.params is None
        assert ctx.message is None
        assert ctx.resume_session is False

    def test_full_creation(self):
        """Full context with all fields works."""
        ctx = RequestContext(
            session_id="abc123",
            action="answer",
            params={"key": "value"},
            message="Hello",
            image="base64data",
            resume_session=True,
            metadata={"user_id": "123"},
        )
        assert ctx.params == {"key": "value"}
        assert ctx.message == "Hello"
        assert ctx.image == "base64data"
        assert ctx.resume_session is True
        assert ctx.metadata == {"user_id": "123"}

    def test_get_param(self):
        """get_param helper works."""
        ctx = RequestContext(
            session_id="abc",
            action="test",
            params={"name": "Alice", "age": 30},
        )
        assert ctx.get_param("name") == "Alice"
        assert ctx.get_param("age") == 30
        assert ctx.get_param("missing") is None
        assert ctx.get_param("missing", "default") == "default"

    def test_get_param_with_none_params(self):
        """get_param with None params returns default."""
        ctx = RequestContext(session_id="abc", action="test")
        assert ctx.get_param("any") is None
        assert ctx.get_param("any", "default") == "default"


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_basic_creation(self):
        """Basic result creation works."""
        result = ExecutionResult(
            state={"request": {"action": "test"}},
            response_type="interview",
            response_data={"question": "Test?"},
        )
        assert result.state == {"request": {"action": "test"}}
        assert result.response_type == "interview"
        assert result.success is True
        assert result.error is None

    def test_from_state(self):
        """from_state extracts response correctly."""
        state = {
            "response": {
                "response_type": "proposals",
                "response_data": {"items": [1, 2, 3]},
                "response_message": "Here are some options",
            }
        }
        result = ExecutionResult.from_state(state)
        
        assert result.response_type == "proposals"
        assert result.response_data == {"items": [1, 2, 3]}
        assert result.response_message == "Here are some options"
        assert result.success is True

    def test_error_result(self):
        """error_result creates failure result."""
        result = ExecutionResult.error_result("Something went wrong")
        
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.state == {}

    def test_to_response_dict_success(self):
        """to_response_dict for success case."""
        result = ExecutionResult(
            state={},
            response_type="interview",
            response_data={"question": "Test?", "options": ["A", "B"]},
        )
        response = result.to_response_dict()
        
        assert response["type"] == "interview"
        assert response["question"] == "Test?"
        assert response["options"] == ["A", "B"]

    def test_to_response_dict_error(self):
        """to_response_dict for error case."""
        result = ExecutionResult.error_result("Failed")
        response = result.to_response_dict()
        
        assert response["type"] == "error"
        assert response["error"] == "Failed"


class TestDefaultHooks:
    """Tests for DefaultHooks."""

    @pytest.mark.asyncio
    async def test_prepare_state_returns_unchanged(self):
        """prepare_state returns state unchanged."""
        hooks = DefaultHooks()
        state = {"request": {"action": "test"}}
        ctx = RequestContext(session_id="abc", action="test")
        
        result = await hooks.prepare_state(state, ctx)
        assert result == state

    @pytest.mark.asyncio
    async def test_after_execution_does_nothing(self):
        """after_execution completes without error."""
        hooks = DefaultHooks()
        state = {"response": {"response_type": "test"}}
        result = ExecutionResult.from_state(state)
        
        # Should not raise
        await hooks.after_execution(state, result)


class TestInMemorySessionStore:
    """Tests for InMemorySessionStore."""

    @pytest.mark.asyncio
    async def test_save_and_load(self):
        """save and load work correctly."""
        store = InMemorySessionStore()
        
        await store.save("session1", {"user": "test", "count": 1})
        data = await store.load("session1")
        
        assert data == {"user": "test", "count": 1}

    @pytest.mark.asyncio
    async def test_load_nonexistent(self):
        """load returns None for nonexistent session."""
        store = InMemorySessionStore()
        data = await store.load("nonexistent")
        assert data is None

    @pytest.mark.asyncio
    async def test_delete(self):
        """delete removes session."""
        store = InMemorySessionStore()
        
        await store.save("session1", {"data": "test"})
        await store.delete("session1")
        data = await store.load("session1")
        
        assert data is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_no_error(self):
        """delete on nonexistent session doesn't error."""
        store = InMemorySessionStore()
        await store.delete("nonexistent")  # Should not raise

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """sessions expire after TTL."""
        store = InMemorySessionStore()
        
        # Save with very short TTL
        await store.save("session1", {"data": "test"}, ttl_seconds=0)
        
        # Wait a tiny bit more than 0 seconds
        await asyncio.sleep(0.01)
        
        # Should be expired
        data = await store.load("session1")
        assert data is None

    def test_len(self):
        """__len__ returns session count."""
        store = InMemorySessionStore()
        assert len(store) == 0
        
        asyncio.get_event_loop().run_until_complete(
            store.save("s1", {"a": 1})
        )
        assert len(store) == 1

    def test_clear(self):
        """clear removes all sessions."""
        store = InMemorySessionStore()
        asyncio.get_event_loop().run_until_complete(store.save("s1", {}))
        asyncio.get_event_loop().run_until_complete(store.save("s2", {}))
        
        store.clear()
        assert len(store) == 0


class TestAgentRuntime:
    """Tests for AgentRuntime execution engine."""

    @pytest.mark.asyncio
    async def test_execute_basic(self):
        """Basic execution without hooks or session."""
        # Mock graph
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "request": {"action": "test"},
            "response": {
                "response_type": "success",
                "response_data": {"message": "Done"},
            },
        }
        
        runtime = AgentRuntime(graph=mock_graph)
        result = await runtime.execute(RequestContext(
            session_id="abc123",
            action="test",
        ))
        
        assert result.success is True
        assert result.response_type == "success"
        assert result.response_data == {"message": "Done"}
        mock_graph.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_session_restore(self):
        """Execution restores session data."""
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"response": {"response_type": "ok"}}
        
        store = InMemorySessionStore()
        await store.save("session1", {
            "workflow": {"collected_info": {"name": "Alice"}},
        })
        
        # Need to explicitly specify slices_to_restore now
        runtime = AgentRuntime(
            graph=mock_graph,
            session_store=store,
            slices_to_restore=["_internal", "workflow"],
        )
        await runtime.execute(RequestContext(
            session_id="session1",
            action="answer",
            resume_session=True,
        ))
        
        # Check that graph was called with merged state
        call_args = mock_graph.ainvoke.call_args[0][0]
        assert call_args.get("workflow", {}).get("collected_info") == {"name": "Alice"}

    @pytest.mark.asyncio
    async def test_execute_with_hooks(self):
        """Execution calls hooks correctly."""
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"response": {"response_type": "ok"}}
        
        # Custom hooks
        class TestHooks:
            def __init__(self):
                self.prepare_called = False
                self.after_called = False
            
            async def prepare_state(self, state, request):
                self.prepare_called = True
                return Internal.active_mode.set(state, "custom_mode")
            
            async def after_execution(self, state, result):
                self.after_called = True
        
        hooks = TestHooks()
        runtime = AgentRuntime(graph=mock_graph, hooks=hooks)
        
        await runtime.execute(RequestContext(session_id="abc", action="test"))
        
        assert hooks.prepare_called is True
        assert hooks.after_called is True
        
        # Verify hook modified state
        call_args = mock_graph.ainvoke.call_args[0][0]
        assert Internal.active_mode.get(call_args) == "custom_mode"

    @pytest.mark.asyncio
    async def test_execute_handles_error(self):
        """Execution handles graph errors gracefully."""
        mock_graph = AsyncMock()
        mock_graph.ainvoke.side_effect = RuntimeError("Graph failed")
        
        runtime = AgentRuntime(graph=mock_graph)
        result = await runtime.execute(RequestContext(
            session_id="abc",
            action="test",
        ))
        
        assert result.success is False
        assert "Graph failed" in result.error

    @pytest.mark.asyncio
    async def test_initial_state_structure(self):
        """Initial state has correct structure."""
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"response": {}}
        
        runtime = AgentRuntime(graph=mock_graph)
        await runtime.execute(RequestContext(
            session_id="abc123",
            action="answer",
            params={"key": "value"},
            message="Hello",
        ))
        
        call_args = mock_graph.ainvoke.call_args[0][0]
        
        # Check request slice
        assert Request.session_id.get(call_args) == "abc123"
        assert Request.action.get(call_args) == "answer"
        assert Request.params.get(call_args) == {"key": "value"}
        assert Request.message.get(call_args) == "Hello"
        
        # Check internal slice initialized
        assert Internal.turn_count.get(call_args) == 0
        assert Internal.is_first_turn.get(call_args) is True
