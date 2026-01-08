#!/usr/bin/env python3
"""
Example: Simple Chatbot
=======================

The simplest possible agent-contracts example.
A 3-node chatbot that handles greetings, farewells, and unknown intents.

This example demonstrates:
- NodeContract definition
- TriggerCondition with priority
- GenericSupervisor for routing decisions
- Rule-based routing (no LLM required)

Run with:
    python examples/03_simple_chatbot.py
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
    GenericSupervisor,
)


# =============================================================================
# Nodes
# =============================================================================

class GreetingNode(ModularNode):
    """Handles greeting messages."""
    
    CONTRACT = NodeContract(
        name="greeting",
        description="Responds to greetings like 'hello', 'hi'",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        is_terminal=True,
        trigger_conditions=[
            TriggerCondition(
                priority=10,
                when={"request.intent": "greet"},
                llm_hint="Use when user says hello, hi, hey, etc.",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        request = inputs.get_slice("request")
        user_name = request.get("user_name", "there")
        
        return NodeOutputs(
            response={
                "response_type": "greeting",
                "response_data": {
                    "message": f"Hello, {user_name}! How can I help you today?",
                },
            }
        )


class FarewellNode(ModularNode):
    """Handles farewell messages."""
    
    CONTRACT = NodeContract(
        name="farewell",
        description="Responds to farewells like 'bye', 'goodbye'",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        is_terminal=True,
        trigger_conditions=[
            TriggerCondition(
                priority=10,
                when={"request.intent": "farewell"},
                llm_hint="Use when user says bye, goodbye, see you, etc.",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        request = inputs.get_slice("request")
        user_name = request.get("user_name", "")
        
        name_part = f", {user_name}" if user_name else ""
        
        return NodeOutputs(
            response={
                "response_type": "farewell",
                "response_data": {
                    "message": f"Goodbye{name_part}! Have a great day!",
                },
            }
        )


class DefaultNode(ModularNode):
    """Fallback for unknown intents."""
    
    CONTRACT = NodeContract(
        name="default",
        description="Handles unknown or unclear requests",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        is_terminal=True,
        trigger_conditions=[
            TriggerCondition(
                priority=1,  # Lowest priority - fallback
                llm_hint="Use when intent is unclear",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(
            response={
                "response_type": "default",
                "response_data": {
                    "message": "I'm not sure what you mean. Try saying 'hello' or 'goodbye'!",
                },
            }
        )


# =============================================================================
# Demo
# =============================================================================

async def run_chatbot(intent: str, user_name: str = "User"):
    """Run the chatbot with a given intent."""
    
    # Setup registry
    registry = NodeRegistry()
    registry.register(GreetingNode)
    registry.register(FarewellNode)
    registry.register(DefaultNode)
    
    # Create supervisor (no LLM - rule-based only)
    supervisor = GenericSupervisor(
        supervisor_name="main",
        llm=None,
        registry=registry,
        max_iterations=10,
        terminal_response_types={"greeting", "farewell", "default"},
    )
    
    # Create state
    state = {
        "request": {
            "intent": intent,
            "user_name": user_name,
        },
        "response": {},
        "_internal": {},
    }
    
    # Get routing decision
    decision = await supervisor.decide_with_trace(state)
    
    # Execute the selected node
    node_instances = {
        "greeting": GreetingNode(llm=None),
        "farewell": FarewellNode(llm=None),
        "default": DefaultNode(llm=None),
    }
    
    if decision.selected_node in node_instances:
        node = node_instances[decision.selected_node]
        inputs = NodeInputs(request=state["request"])
        outputs = await node.execute(inputs)
        return outputs.to_state_updates().get("response", {})
    
    return {"error": "No node selected"}


async def main():
    """Demo the simple chatbot."""
    print()
    print("🤖 Simple Chatbot Demo")
    print("=" * 50)
    print()
    
    # Test greeting
    print("📨 User intent: 'greet' (name: Alice)")
    response = await run_chatbot("greet", "Alice")
    print(f"🤖 Response: {response.get('response_data', {}).get('message')}")
    print()
    
    # Test farewell
    print("📨 User intent: 'farewell' (name: Bob)")
    response = await run_chatbot("farewell", "Bob")
    print(f"🤖 Response: {response.get('response_data', {}).get('message')}")
    print()
    
    # Test unknown
    print("📨 User intent: 'unknown'")
    response = await run_chatbot("unknown", "")
    print(f"🤖 Response: {response.get('response_data', {}).get('message')}")
    print()
    
    print("=" * 50)
    print("✅ Demo completed!")
    print()


if __name__ == "__main__":
    asyncio.run(main())
