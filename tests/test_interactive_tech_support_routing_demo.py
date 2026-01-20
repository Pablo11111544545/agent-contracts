import sys
from pathlib import Path

import pytest

# Pytest 9's default import mode can run without adding the repo root to sys.path
# (e.g., when invoked via the `pytest` entrypoint). The demo lives under
# `./examples/`, so ensure the repo root is importable for this test module.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_contracts import GenericSupervisor, NodeRegistry

from examples.interactive_tech_support.nodes import (
    ClassificationNode,
    HardwareNode,
    SoftwareNode,
    NetworkNode,
    GeneralNode,
    ClarificationNode,
)


def _build_demo_registry() -> NodeRegistry:
    registry = NodeRegistry(
        valid_slices={"request", "routing", "response", "support_context", "_internal"}
    )
    registry.register(ClassificationNode)
    registry.register(HardwareNode)
    registry.register(SoftwareNode)
    registry.register(NetworkNode)
    registry.register(GeneralNode)
    registry.register(ClarificationNode)
    return registry


def _apply_updates(state: dict, updates: dict) -> None:
    for key, value in (updates or {}).items():
        if isinstance(value, dict) and isinstance(state.get(key), dict):
            state[key].update(value)
        else:
            state[key] = value


@pytest.mark.asyncio
async def test_demo_routes_wifi_to_network_without_llm():
    registry = _build_demo_registry()
    supervisor = GenericSupervisor(
        supervisor_name="tech_support",
        llm=None,
        registry=registry,
        terminal_response_types={"answer", "error", "goodbye"},
    )

    state = {
        "request": {"message": "My wifi keeps disconnecting", "session_id": "s"},
        "routing": {"category": None},
        "response": {},
        "support_context": {},
        "_internal": {"needs_classification": True, "needs_clarification": False},
    }

    decision1 = await supervisor.decide_with_trace(state)
    assert decision1.selected_node == "classification"

    classification = ClassificationNode(llm=None)
    _apply_updates(state, await classification(state))

    decision2 = await supervisor.decide_with_trace(state)
    assert decision2.selected_node == "network_support"


@pytest.mark.asyncio
async def test_demo_routes_unknown_to_clarification_without_llm():
    registry = _build_demo_registry()
    supervisor = GenericSupervisor(
        supervisor_name="tech_support",
        llm=None,
        registry=registry,
        terminal_response_types={"answer", "error", "goodbye"},
    )

    state = {
        "request": {"message": "hello", "session_id": "s"},
        "routing": {"category": None},
        "response": {},
        "support_context": {},
        "_internal": {"needs_classification": True, "needs_clarification": False},
    }

    decision1 = await supervisor.decide_with_trace(state)
    assert decision1.selected_node == "classification"

    classification = ClassificationNode(llm=None)
    _apply_updates(state, await classification(state))

    decision2 = await supervisor.decide_with_trace(state)
    assert decision2.selected_node == "clarification"


@pytest.mark.asyncio
async def test_demo_routes_password_reset_to_general_without_llm():
    registry = _build_demo_registry()
    supervisor = GenericSupervisor(
        supervisor_name="tech_support",
        llm=None,
        registry=registry,
        terminal_response_types={"answer", "error", "goodbye"},
    )

    state = {
        "request": {"message": "How do I reset my password?", "session_id": "s"},
        "routing": {"category": None},
        "response": {},
        "support_context": {},
        "_internal": {"needs_classification": True, "needs_clarification": False},
    }

    decision1 = await supervisor.decide_with_trace(state)
    assert decision1.selected_node == "classification"

    classification = ClassificationNode(llm=None)
    _apply_updates(state, await classification(state))

    decision2 = await supervisor.decide_with_trace(state)
    assert decision2.selected_node == "general_support"
