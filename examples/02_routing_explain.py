#!/usr/bin/env python3
"""
Example: Routing Explanation
============================

Demonstrates the Traceable Routing feature:
1. TriggerCondition matching with priority
2. RoutingDecision structured output
3. Decision type explanation (rule_match, terminal_state, etc.)

Run with:
    python examples/02_routing_explain.py
"""

import sys
import asyncio

sys.path.insert(0, "src")

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
    RoutingDecision,
)
from agent_contracts.registry import NodeRegistry
from agent_contracts.supervisor import GenericSupervisor


# =============================================================================
# Example Nodes
# =============================================================================

class SearchNode(ModularNode):
    """Search handler node."""
    CONTRACT = NodeContract(
        name="search",
        description="Handles product search requests",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=100,
                when={"request.action": "search"},
                llm_hint="Use when user wants to search for products",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"type": "search_results"})


class RecommendNode(ModularNode):
    """Recommendation handler node."""
    CONTRACT = NodeContract(
        name="recommend",
        description="Provides personalized recommendations",
        reads=["request", "context"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=50,
                when={"request.action": "recommend"},
                llm_hint="Use when user wants recommendations",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"type": "recommendations"})


class FallbackNode(ModularNode):
    """Fallback handler node."""
    CONTRACT = NodeContract(
        name="fallback",
        description="Default handler for unrecognized requests",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=1,
                llm_hint="Use as fallback when no other handler matches",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"type": "fallback"})


# =============================================================================
# Helper Functions
# =============================================================================

def print_routing_decision(decision: RoutingDecision, title: str):
    """Pretty print a routing decision."""
    print(f"\n{'='*60}")
    print(f"📍 {title}")
    print(f"{'='*60}")
    print(f"Selected Node: {decision.selected_node}")
    print(f"Decision Type: {decision.reason.decision_type}")
    
    if decision.reason.matched_rules:
        print(f"\nMatched Rules (by priority):")
        for rule in decision.reason.matched_rules:
            priority_icon = "🔴" if rule.priority >= 100 else "🟡" if rule.priority >= 50 else "🟢"
            print(f"  {priority_icon} P{rule.priority}: {rule.node}")
            print(f"      Condition: {rule.condition}")
    
    if decision.reason.llm_used:
        print(f"\nLLM Used: Yes")
        if decision.reason.llm_reasoning:
            print(f"LLM Reasoning: {decision.reason.llm_reasoning}")
    else:
        print(f"\nLLM Used: No (rule-based only)")


# =============================================================================
# Demo
# =============================================================================

async def demo_search_action():
    """Demo: High priority search action."""
    registry = NodeRegistry()
    registry.add_valid_slice("context")
    registry.register(SearchNode)
    registry.register(RecommendNode)
    registry.register(FallbackNode)
    
    supervisor = GenericSupervisor(
        supervisor_name="main",
        llm=None,  # No LLM for rule-based demo
        registry=registry,
        max_iterations=10,
        terminal_response_types={"final"},
    )
    
    state = {
        "request": {"action": "search", "query": "winter jacket"},
        "_internal": {},
    }
    
    decision = await supervisor.decide_with_trace(state)
    print_routing_decision(decision, "Search Action (High Priority)")


async def demo_recommend_action():
    """Demo: Medium priority recommend action."""
    registry = NodeRegistry()
    registry.add_valid_slice("context")
    registry.register(SearchNode)
    registry.register(RecommendNode)
    registry.register(FallbackNode)
    
    supervisor = GenericSupervisor(
        supervisor_name="main",
        llm=None,
        registry=registry,
        max_iterations=10,
        terminal_response_types={"final"},
    )
    
    state = {
        "request": {"action": "recommend"},
        "_internal": {},
    }
    
    decision = await supervisor.decide_with_trace(state)
    print_routing_decision(decision, "Recommend Action (Medium Priority)")


async def demo_unknown_action():
    """Demo: Unknown action falls back to low priority."""
    registry = NodeRegistry()
    registry.add_valid_slice("context")
    registry.register(SearchNode)
    registry.register(RecommendNode)
    registry.register(FallbackNode)
    
    supervisor = GenericSupervisor(
        supervisor_name="main",
        llm=None,
        registry=registry,
        max_iterations=10,
        terminal_response_types={"final"},
    )
    
    state = {
        "request": {"action": "unknown_action"},
        "_internal": {},
    }
    
    decision = await supervisor.decide_with_trace(state)
    print_routing_decision(decision, "Unknown Action (Fallback)")


async def demo_terminal_state():
    """Demo: Terminal state detection."""
    registry = NodeRegistry()
    registry.add_valid_slice("context")
    registry.register(SearchNode)
    registry.register(RecommendNode)
    registry.register(FallbackNode)
    
    supervisor = GenericSupervisor(
        supervisor_name="main",
        llm=None,
        registry=registry,
        max_iterations=10,
        terminal_response_types={"final", "error"},
    )
    
    state = {
        "request": {"action": "search"},
        "response": {"response_type": "final"},  # Terminal state!
        "_internal": {},
    }
    
    decision = await supervisor.decide_with_trace(state)
    print_routing_decision(decision, "Terminal State")


async def demo_explicit_routing():
    """Demo: Explicit routing (answer to question owner)."""
    registry = NodeRegistry()
    registry.add_valid_slice("context")
    registry.add_valid_slice("interview")
    registry.register(SearchNode)
    registry.register(RecommendNode)
    registry.register(FallbackNode)
    
    supervisor = GenericSupervisor(
        supervisor_name="main",
        llm=None,
        registry=registry,
        max_iterations=10,
        terminal_response_types={"final"},
    )
    
    state = {
        "request": {"action": "answer", "message": "Yes, I like it"},
        "interview": {"last_question": {"node_id": "interviewer_node"}},
        "_internal": {},
    }
    
    decision = await supervisor.decide_with_trace(state)
    print_routing_decision(decision, "Explicit Routing (Answer)")


async def main():
    """Run all demos."""
    print()
    print("🔀 Traceable Routing Demo")
    print("=" * 60)
    print("This demo shows how routing decisions are made and explained.")
    
    await demo_search_action()
    await demo_recommend_action()
    await demo_unknown_action()
    await demo_terminal_state()
    await demo_explicit_routing()
    
    print(f"\n{'='*60}")
    print("✅ All routing demos completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
