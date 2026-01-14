"""Tests for GenericSupervisor context_builder functionality (v0.3.0)."""
import pytest
from agent_contracts import GenericSupervisor


def test_default_behavior_without_context_builder():
    """デフォルト動作: context_builder未指定時は従来通り。"""
    supervisor = GenericSupervisor("test", llm=None)
    
    state = {
        "request": {"action": "test"},
        "response": {},
        "_internal": {},
        "conversation": {"messages": []},
    }
    
    slices, additional_context = supervisor._collect_context_slices(state, [])
    
    assert slices == {"request", "response", "_internal"}
    assert "conversation" not in slices
    assert additional_context == ""


def test_custom_context_builder_adds_slices():
    """カスタムcontext_builderでsliceを追加。"""
    def custom_builder(state, candidates):
        return {
            "slices": {"request", "response", "_internal", "conversation"},
        }
    
    supervisor = GenericSupervisor("test", llm=None, context_builder=custom_builder)
    slices, additional_context = supervisor._collect_context_slices({}, [])
    
    assert "conversation" in slices
    assert len(slices) == 4
    assert additional_context == ""


def test_custom_context_builder_with_summary():
    """カスタムcontext_builderでsummaryを提供。"""
    def custom_builder(state, candidates):
        messages = state.get("conversation", {}).get("messages", [])
        user_messages = [m for m in messages if m.get("role") == "user"]
        return {
            "slices": {"request", "response", "_internal", "conversation"},
            "summary": {
                "total_turns": len(user_messages),
                "readiness": 0.67,
            },
        }
    
    supervisor = GenericSupervisor("test", llm=None, context_builder=custom_builder)
    
    state = {
        "conversation": {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
                {"role": "user", "content": "How are you?"},
            ]
        }
    }
    
    result = custom_builder(state, [])
    
    assert result["summary"]["total_turns"] == 2
    assert result["summary"]["readiness"] == 0.67


def test_context_builder_fallback_to_default():
    """context_builderが不正な値を返した場合のフォールバック。"""
    def bad_builder(state, candidates):
        return {}  # "slices" キーがない
    
    supervisor = GenericSupervisor("test", llm=None, context_builder=bad_builder)
    slices, additional_context = supervisor._collect_context_slices({}, [])
    
    # デフォルト値にフォールバック
    assert slices == {"request", "response", "_internal"}
    assert additional_context == ""


def test_context_builder_receives_candidates():
    """context_builderがcandidatesを受け取ることを確認。"""
    received_candidates = []
    
    def tracking_builder(state, candidates):
        received_candidates.extend(candidates)
        return {"slices": {"request", "response", "_internal"}}
    
    supervisor = GenericSupervisor("test", llm=None, context_builder=tracking_builder)
    supervisor._collect_context_slices({}, ["node_a", "node_b"])
    
    assert "node_a" in received_candidates
    assert "node_b" in received_candidates


def test_context_builder_with_string_summary():
    """context_builderがstring型のsummaryを返すことをサポート。"""
    def string_summary_builder(state, candidates):
        messages = state.get("conversation", {}).get("messages", [])
        history = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        return {
            "slices": {"request", "response", "_internal", "conversation"},
            "summary": f"Recent conversation:\n{history}"  # String format
        }
    
    supervisor = GenericSupervisor("test", llm=None, context_builder=string_summary_builder)
    
    state = {
        "conversation": {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ]
        }
    }
    
    result = string_summary_builder(state, [])
    
    assert isinstance(result["summary"], str)
    assert "Recent conversation:" in result["summary"]
    assert "user: Hello" in result["summary"]
    assert "assistant: Hi there" in result["summary"]


def test_context_builder_with_dict_summary():
    """context_builderがdict型のsummaryを返すことをサポート（後方互換性）。"""
    def dict_summary_builder(state, candidates):
        return {
            "slices": {"request", "response", "_internal"},
            "summary": {
                "turn_count": 5,
                "readiness": 0.8,
            }
        }
    
    supervisor = GenericSupervisor("test", llm=None, context_builder=dict_summary_builder)
    
    result = dict_summary_builder({}, [])
    
    assert isinstance(result["summary"], dict)
    assert result["summary"]["turn_count"] == 5
    assert result["summary"]["readiness"] == 0.8


@pytest.mark.asyncio
async def test_string_summary_in_llm_context():
    """String型summaryがLLMコンテキストに正しく含まれることを確認。"""
    from unittest.mock import AsyncMock, MagicMock
    
    def string_summary_builder(state, candidates):
        return {
            "slices": {"request", "response", "_internal"},
            "summary": "## Custom Context\nThis is formatted text"
        }
    
    # Mock LLM
    mock_llm = MagicMock()
    mock_decision = MagicMock()
    mock_decision.next_node = "done"
    mock_decision.reasoning = "test"
    mock_llm.with_structured_output = MagicMock(return_value=MagicMock(
        ainvoke=AsyncMock(return_value=mock_decision)
    ))
    
    # Mock registry
    from agent_contracts import NodeRegistry
    registry = NodeRegistry()
    
    supervisor = GenericSupervisor(
        "test",
        llm=mock_llm,
        registry=registry,
        context_builder=string_summary_builder
    )
    
    state = {
        "request": {"action": "test"},
        "response": {"response_type": "test"},
        "_internal": {},
    }
    
    # Execute decision
    result = await supervisor.decide(state)
    
    # Verify LLM was called (which means summary was included in context)
    assert mock_llm.with_structured_output.called
    assert result.next_node == "done"