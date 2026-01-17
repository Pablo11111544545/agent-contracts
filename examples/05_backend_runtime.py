#!/usr/bin/env python3
"""
Example: Backend Runtime
=======================

Demonstrates how to build a backend-oriented agent with:
- Contract validation (strict)
- GraphBuilder + AgentRuntime
- Rule-based routing (no LLM required)

Run with:
    python examples/05_backend_runtime.py
"""

import asyncio
import sys
sys.path.insert(0, "src")

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
    NodeRegistry,
    ContractValidator,
    BaseAgentState,
    build_graph_from_registry,
)
from agent_contracts.runtime import AgentRuntime, RequestContext


# =============================================================================
# Nodes
# =============================================================================

class CreateTicketNode(ModularNode):
    """Creates a support ticket."""

    CONTRACT = NodeContract(
        name="create_ticket",
        description="Create a new support ticket",
        reads=["request", "ticket"],
        writes=["ticket", "response"],
        supervisor="main",
        is_terminal=True,
        trigger_conditions=[
            TriggerCondition(
                priority=50,
                when={"request.action": "create_ticket"},
                llm_hint="Create a support ticket",
            )
        ],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        request = inputs.get_slice("request")
        params = request.get("params") or {}
        title = params.get("title", "Untitled")
        ticket_id = "TCK-1001"
        return NodeOutputs(
            ticket={"id": ticket_id, "title": title, "status": "open"},
            response={
                "response_type": "ticket_created",
                "response_data": {"ticket_id": ticket_id, "title": title},
            },
        )


class TicketStatusNode(ModularNode):
    """Returns ticket status."""

    CONTRACT = NodeContract(
        name="ticket_status",
        description="Fetch ticket status by ID",
        reads=["request", "ticket"],
        writes=["response"],
        supervisor="main",
        is_terminal=True,
        trigger_conditions=[
            TriggerCondition(
                priority=50,
                when={"request.action": "ticket_status"},
                llm_hint="Return ticket status",
            )
        ],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        request = inputs.get_slice("request")
        params = request.get("params") or {}
        ticket_id = params.get("ticket_id", "unknown")
        return NodeOutputs(
            response={
                "response_type": "ticket_status",
                "response_data": {"ticket_id": ticket_id, "status": "open"},
            },
        )


class FallbackNode(ModularNode):
    """Fallback handler."""

    CONTRACT = NodeContract(
        name="fallback",
        description="Fallback for unsupported actions",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        is_terminal=True,
        trigger_conditions=[TriggerCondition(priority=1)],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(
            response={
                "response_type": "error",
                "response_data": {"message": "Unsupported action"},
            },
        )


# =============================================================================
# Demo
# =============================================================================

def build_runtime() -> AgentRuntime:
    registry = NodeRegistry()
    registry.add_valid_slice("ticket")
    registry.register(CreateTicketNode)
    registry.register(TicketStatusNode)
    registry.register(FallbackNode)

    validator = ContractValidator(registry, strict=True)
    result = validator.validate()
    if result.has_errors:
        raise SystemExit(str(result))

    graph = build_graph_from_registry(
        registry=registry,
        supervisors=["main"],
        state_class=BaseAgentState,
    )
    graph.set_entry_point("main_supervisor")
    compiled = graph.compile()

    return AgentRuntime(compiled)


async def main() -> None:
    runtime = build_runtime()

    create_request = RequestContext(
        session_id="demo-1",
        action="create_ticket",
        params={"title": "Login issue"},
    )
    create_result = await runtime.execute(create_request)
    print("Create:", create_result.to_response_dict())

    status_request = RequestContext(
        session_id="demo-2",
        action="ticket_status",
        params={"ticket_id": "TCK-1001"},
    )
    status_result = await runtime.execute(status_request)
    print("Status:", status_result.to_response_dict())


if __name__ == "__main__":
    asyncio.run(main())
