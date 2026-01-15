"""Tests for Traceable Routing (RoutingDecision)."""
import pytest

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
    TriggerMatch,
    RoutingDecision,
    RoutingReason,
    MatchedRule,
)
from agent_contracts.registry import NodeRegistry
from agent_contracts.supervisor import GenericSupervisor


# =============================================================================
# Test Fixtures
# =============================================================================

class HighPriorityNode(ModularNode):
    """High priority node."""
    CONTRACT = NodeContract(
        name="high_priority",
        description="High priority action",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=100,
                when={"request.action": "urgent"},
                llm_hint="Handle urgent requests",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class MediumPriorityNode(ModularNode):
    """Medium priority node."""
    CONTRACT = NodeContract(
        name="medium_priority",
        description="Medium priority action",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=50,
                when={"request.action": "search"},
                llm_hint="Handle search requests",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class LowPriorityNode(ModularNode):
    """Low priority fallback node."""
    CONTRACT = NodeContract(
        name="low_priority",
        description="Low priority fallback",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=10,
                llm_hint="Fallback handler",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class TerminalNode(ModularNode):
    """Terminal node."""
    CONTRACT = NodeContract(
        name="terminal",
        description="Terminal node",
        reads=["response"],
        writes=["response"],
        supervisor="main",
        is_terminal=True,
        trigger_conditions=[
            TriggerCondition(priority=1)
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


# =============================================================================
# Tests for RoutingDecision Types
# =============================================================================

class TestRoutingTypes:
    """Tests for routing type models."""
    
    def test_matched_rule_creation(self):
        """MatchedRule should be created correctly."""
        rule = MatchedRule(
            node="test_node",
            condition="request.action=test",
            priority=10,
        )
        assert rule.node == "test_node"
        assert rule.condition == "request.action=test"
        assert rule.priority == 10
    
    def test_routing_reason_creation(self):
        """RoutingReason should be created correctly."""
        reason = RoutingReason(
            decision_type="rule_match",
            matched_rules=[
                MatchedRule(node="a", condition="x=1", priority=10),
                MatchedRule(node="b", condition="y=2", priority=5),
            ],
            llm_used=False,
        )
        assert reason.decision_type == "rule_match"
        assert len(reason.matched_rules) == 2
        assert not reason.llm_used
    
    def test_routing_decision_creation(self):
        """RoutingDecision should be created correctly."""
        decision = RoutingDecision(
            selected_node="test_node",
            reason=RoutingReason(decision_type="rule_match"),
        )
        assert decision.selected_node == "test_node"
        assert decision.reason.decision_type == "rule_match"
    
    def test_routing_decision_to_supervisor_decision(self):
        """RoutingDecision should convert to SupervisorDecision."""
        decision = RoutingDecision(
            selected_node="test_node",
            reason=RoutingReason(
                decision_type="rule_match",
                matched_rules=[
                    MatchedRule(node="test_node", condition="x=1", priority=10),
                ],
            ),
        )
        supervisor_decision = decision.to_supervisor_decision()
        assert supervisor_decision.next_node == "test_node"
        assert "rule_match" in supervisor_decision.reasoning


# =============================================================================
# Tests for GenericSupervisor.decide_with_trace
# =============================================================================

class TestDecideWithTrace:
    """Tests for decide_with_trace method."""
    
    @pytest.fixture
    def registry(self):
        """Create a registry with test nodes."""
        reg = NodeRegistry()
        reg.register(HighPriorityNode)
        reg.register(MediumPriorityNode)
        reg.register(LowPriorityNode)
        reg.register(TerminalNode)
        return reg
    
    @pytest.fixture
    def supervisor(self, registry):
        """Create a supervisor without LLM."""
        return GenericSupervisor(
            supervisor_name="main",
            llm=None,
            registry=registry,
            max_iterations=10,
            terminal_response_types={"final"},
        )
    
    @pytest.mark.asyncio
    async def test_rule_match_high_priority(self, supervisor):
        """High priority rule should match first."""
        state = {
            "request": {"action": "urgent"},
            "_internal": {},
        }
        
        decision = await supervisor.decide_with_trace(state)
        
        assert decision.selected_node == "high_priority"
        assert decision.reason.decision_type == "rule_match"
        assert len(decision.reason.matched_rules) > 0
        assert decision.reason.matched_rules[0].node == "high_priority"
        assert decision.reason.matched_rules[0].priority == 100
    
    @pytest.mark.asyncio
    async def test_rule_match_medium_priority(self, supervisor):
        """Medium priority rule should match for search action."""
        state = {
            "request": {"action": "search"},
            "_internal": {},
        }
        
        decision = await supervisor.decide_with_trace(state)
        
        assert decision.selected_node == "medium_priority"
        assert decision.reason.decision_type == "rule_match"
    
    @pytest.mark.asyncio
    async def test_rule_match_fallback(self, supervisor):
        """Low priority should be selected when no specific match."""
        state = {
            "request": {"action": "unknown"},
            "_internal": {},
        }
        
        decision = await supervisor.decide_with_trace(state)
        
        # Low priority is the only one that matches (no 'when' condition)
        assert decision.selected_node == "low_priority"
        assert decision.reason.decision_type == "rule_match"
    
    @pytest.mark.asyncio
    async def test_terminal_state(self, supervisor):
        """Terminal state should return done."""
        state = {
            "request": {},
            "response": {"response_type": "final"},
            "_internal": {},
        }
        
        decision = await supervisor.decide_with_trace(state)
        
        assert decision.selected_node == "done"
        assert decision.reason.decision_type == "terminal_state"
    
    @pytest.mark.asyncio
    async def test_explicit_routing(self):
        """Explicit routing handler routes correctly when returning valid node."""
        # Create custom handler for testing - returns a valid registered node
        def test_router(state: dict) -> str | None:
            req = state.get("request", {})
            if req.get("action") == "answer":
                interview = state.get("interview", {})
                last_q = interview.get("last_question", {})
                if isinstance(last_q, dict):
                    return last_q.get("node_id")
            return None
        
        registry = NodeRegistry()
        registry.register(HighPriorityNode)
        registry.register(LowPriorityNode)
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=None,
            registry=registry,
            explicit_routing_handler=test_router,
        )
        
        # Use a valid registered node name
        state = {
            "request": {"action": "answer"},
            "interview": {
                "last_question": {"node_id": "high_priority"}  # Valid node
            },
            "_internal": {},
        }
        
        decision = await supervisor.decide_with_trace(state)
        
        assert decision.selected_node == "high_priority"
        assert decision.reason.decision_type == "explicit_routing"
    
    @pytest.mark.asyncio
    async def test_explicit_routing_invalid_node_fallback(self):
        """Explicit routing falls back to normal routing when returning invalid node."""
        # Create custom handler that returns an invalid node name
        def test_router(state: dict) -> str | None:
            return "non_existent_node"  # Invalid node name
        
        registry = NodeRegistry()
        registry.register(HighPriorityNode)
        registry.register(LowPriorityNode)
        
        supervisor = GenericSupervisor(
            supervisor_name="main",
            llm=None,
            registry=registry,
            explicit_routing_handler=test_router,
        )
        
        state = {
            "request": {"action": "urgent"},  # Matches high_priority
            "_internal": {},
        }
        
        decision = await supervisor.decide_with_trace(state)
        
        # Should fall back to normal rule-based routing
        assert decision.selected_node == "high_priority"
        assert decision.reason.decision_type == "rule_match"
    
    @pytest.mark.asyncio
    async def test_matched_rules_contain_condition_description(self, supervisor):
        """Matched rules should have human-readable condition descriptions."""
        state = {
            "request": {"action": "urgent"},
            "_internal": {},
        }
        
        decision = await supervisor.decide_with_trace(state)
        
        high_prio_rule = next(
            (r for r in decision.reason.matched_rules if r.node == "high_priority"),
            None
        )
        assert high_prio_rule is not None
        assert "request.action=urgent" in high_prio_rule.condition
    
    @pytest.mark.asyncio
    async def test_no_llm_used_without_llm(self, supervisor):
        """LLM should not be marked as used when not provided."""
        state = {
            "request": {"action": "search"},
            "_internal": {},
        }
        
        decision = await supervisor.decide_with_trace(state)
        
        assert not decision.reason.llm_used
        assert decision.reason.llm_reasoning is None


class TestBuildMatchedRules:
    """Tests for _build_matched_rules helper."""
    
    @pytest.fixture
    def registry(self):
        """Create a registry with test nodes."""
        reg = NodeRegistry()
        reg.register(HighPriorityNode)
        reg.register(MediumPriorityNode)
        return reg
    
    @pytest.fixture
    def supervisor(self, registry):
        """Create a supervisor."""
        return GenericSupervisor(
            supervisor_name="main",
            llm=None,
            registry=registry,
        )
    
    def test_build_matched_rules(self, supervisor):
        """Should build correct MatchedRule list."""
        matches = [
            TriggerMatch(priority=100, node_name="high_priority", condition_index=0),
            TriggerMatch(priority=50, node_name="medium_priority", condition_index=0)
        ]
        
        rules = supervisor._build_matched_rules(matches)
        
        assert len(rules) == 2
        assert rules[0].node == "high_priority"
        assert rules[0].priority == 100
        assert rules[1].node == "medium_priority"
        assert rules[1].priority == 50
    
    def test_build_matched_rules_empty(self, supervisor):
        """Empty matches should return empty list."""
        rules = supervisor._build_matched_rules([])
        assert rules == []
