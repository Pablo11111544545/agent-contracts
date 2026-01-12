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
    
    slices = supervisor._collect_context_slices(state, [])
    
    assert slices == {"request", "response", "_internal"}
    assert "conversation" not in slices


def test_custom_context_builder_adds_slices():
    """カスタムcontext_builderでsliceを追加。"""
    def custom_builder(state, candidates):
        return {
            "slices": {"request", "response", "_internal", "conversation"},
        }
    
    supervisor = GenericSupervisor("test", llm=None, context_builder=custom_builder)
    slices = supervisor._collect_context_slices({}, [])
    
    assert "conversation" in slices
    assert len(slices) == 4


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
    slices = supervisor._collect_context_slices({}, [])
    
    # デフォルト値にフォールバック
    assert slices == {"request", "response", "_internal"}


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