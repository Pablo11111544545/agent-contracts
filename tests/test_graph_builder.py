"""Tests for GraphBuilder and build_graph_from_registry."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from langgraph.graph import StateGraph, END

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
    NodeRegistry,
    GraphBuilder,
    build_graph_from_registry,
)


# =============================================================================
# Test Nodes (prefixed with Sample to avoid pytest collection)
# =============================================================================

class SampleNodeA(ModularNode):
    """Test node A."""
    CONTRACT = NodeContract(
        name="node_a",
        description="Test node A",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        requires_llm=False,
        trigger_conditions=[
            TriggerCondition(priority=10, when={"request.action": "a"})
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"from": "node_a"})


class SampleNodeB(ModularNode):
    """Test node B (terminal)."""
    CONTRACT = NodeContract(
        name="node_b",
        description="Test node B",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        is_terminal=True,
        trigger_conditions=[
            TriggerCondition(priority=5, when={"request.action": "b"})
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"from": "node_b"})


class SampleNodeWithLLM(ModularNode):
    """Test node that requires LLM."""
    CONTRACT = NodeContract(
        name="node_with_llm",
        description="Node requiring LLM",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        requires_llm=True,
        trigger_conditions=[
            TriggerCondition(priority=1)
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"from": "node_with_llm"})


# =============================================================================
# GraphBuilder Tests
# =============================================================================

class TestGraphBuilder:
    """Tests for GraphBuilder class."""

    @pytest.fixture
    def registry(self):
        """Create registry with test nodes."""
        reg = NodeRegistry()
        reg.register(SampleNodeA)
        reg.register(SampleNodeB)
        return reg

    def test_init_with_registry(self, registry):
        """Test initialization with registry."""
        builder = GraphBuilder(registry=registry)
        
        assert builder.registry is registry
        assert len(builder.supervisor_names) == 0
        assert len(builder.node_classes) == 0

    def test_init_without_registry_uses_global(self):
        """Test initialization without registry uses global."""
        builder = GraphBuilder()
        
        assert builder.registry is not None

    def test_add_supervisor(self, registry):
        """Test adding a supervisor."""
        builder = GraphBuilder(registry=registry)
        
        result = builder.add_supervisor("main", llm=None)
        
        assert result is builder  # Returns self for chaining
        assert "main" in builder.supervisor_names
        assert "node_a" in builder.node_classes
        assert "node_b" in builder.node_classes
        assert "node_a" in builder.node_instances
        assert "node_b" in builder.node_instances

    def test_add_supervisor_with_llm_provider(self, registry):
        """Test adding supervisor with llm_provider skips instance creation."""
        mock_llm_provider = MagicMock(return_value="mock_llm")
        builder = GraphBuilder(registry=registry, llm_provider=mock_llm_provider)
        
        builder.add_supervisor("main")
        
        # With llm_provider, instances are created on-demand, not upfront
        assert "main" in builder.supervisor_names
        assert "node_a" in builder.node_classes
        assert len(builder.node_instances) == 0  # Not created upfront

    def test_build_routing_map(self, registry):
        """Test building routing map."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        
        routing_map = builder.build_routing_map("main")
        
        assert routing_map["node_a"] == "node_a"
        assert routing_map["node_b"] == "node_b"
        assert routing_map["done"] == END

    def test_create_node_wrapper(self, registry):
        """Test creating node wrapper function."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        
        wrapper = builder.create_node_wrapper("node_a")
        
        assert callable(wrapper)
        assert wrapper.__name__ == "node_a_node"

    @pytest.mark.asyncio
    async def test_node_wrapper_executes_node(self, registry):
        """Test that node wrapper executes the node."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        
        wrapper = builder.create_node_wrapper("node_a")
        state = {"request": {"action": "a"}, "response": {}}
        
        result = await wrapper(state)
        
        assert result["response"]["from"] == "node_a"

    @pytest.mark.asyncio
    async def test_node_wrapper_with_missing_class(self, registry):
        """Test node wrapper with missing class returns empty dict."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        # Remove node class to simulate missing
        del builder.node_classes["node_a"]
        
        wrapper = builder.create_node_wrapper("node_a")
        result = await wrapper({})
        
        assert result == {}

    @pytest.mark.asyncio
    async def test_node_wrapper_with_missing_instance(self, registry):
        """Test node wrapper with missing instance returns empty dict."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        # Remove instance to simulate missing
        del builder.node_instances["node_a"]
        
        wrapper = builder.create_node_wrapper("node_a")
        result = await wrapper({})
        
        assert result == {}

    @pytest.mark.asyncio
    async def test_node_wrapper_with_dependency_provider(self, registry):
        """Test node wrapper uses dependency_provider."""
        mock_dep_provider = MagicMock(return_value={})
        builder = GraphBuilder(
            registry=registry,
            dependency_provider=mock_dep_provider,
        )
        builder.add_supervisor("main")
        
        wrapper = builder.create_node_wrapper("node_a")
        state = {"request": {"action": "a"}, "response": {}}
        
        result = await wrapper(state)
        
        mock_dep_provider.assert_called_once()
        assert result["response"]["from"] == "node_a"

    @pytest.mark.asyncio
    async def test_node_wrapper_with_llm_provider(self):
        """Test node wrapper uses llm_provider for nodes requiring LLM."""
        registry = NodeRegistry()
        registry.register(SampleNodeWithLLM)
        
        mock_llm = MagicMock()
        mock_llm_provider = MagicMock(return_value=mock_llm)
        
        builder = GraphBuilder(
            registry=registry,
            llm_provider=mock_llm_provider,
        )
        builder.add_supervisor("main")
        
        wrapper = builder.create_node_wrapper("node_with_llm")
        state = {"request": {}, "response": {}}
        
        result = await wrapper(state)
        
        mock_llm_provider.assert_called()
        assert result["response"]["from"] == "node_with_llm"

    def test_create_supervisor_wrapper(self, registry):
        """Test creating supervisor wrapper."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        
        wrapper = builder.create_supervisor_wrapper("main")
        
        assert callable(wrapper)
        assert wrapper.__name__ == "main_supervisor"

    @pytest.mark.asyncio
    async def test_supervisor_wrapper_with_missing_supervisor(self, registry):
        """Test supervisor wrapper with missing supervisor returns empty dict."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        # Remove supervisor to simulate missing
        del builder.supervisor_instances["main"]
        
        wrapper = builder.create_supervisor_wrapper("main")
        result = await wrapper({})
        
        assert result == {}

    @pytest.mark.asyncio
    async def test_supervisor_wrapper_with_llm_provider(self, registry):
        """Test supervisor wrapper creates supervisor on-demand with llm_provider."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="node_a"))
        mock_llm_provider = MagicMock(return_value=mock_llm)
        
        builder = GraphBuilder(
            registry=registry,
            llm_provider=mock_llm_provider,
        )
        builder.add_supervisor("main")
        
        wrapper = builder.create_supervisor_wrapper("main")
        state = {
            "request": {"action": "a"},
            "response": {},
            "_internal": {},
        }
        
        # Should create supervisor on-demand
        result = await wrapper(state)
        
        mock_llm_provider.assert_called()

    def test_create_routing_function(self, registry):
        """Test creating routing function."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        
        route_fn = builder.create_routing_function("main")
        
        assert callable(route_fn)
        assert route_fn.__name__ == "route_after_main_supervisor"

    def test_routing_function_returns_done_for_terminal_response(self, registry):
        """Test routing returns 'done' for terminal response type."""
        # Set up config with terminal types
        from agent_contracts.config import set_config
        from agent_contracts.config.schema import FrameworkConfig, SupervisorConfig
        config = FrameworkConfig(
            supervisor=SupervisorConfig(
                max_iterations=10,
                terminal_response_types=["interview", "error"],
            )
        )
        set_config(config)
        
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        route_fn = builder.create_routing_function("main")
        
        state = {
            "response": {"response_type": "interview"},  # Terminal type
            "_internal": {"decision": "node_a"},
        }
        
        result = route_fn(state)
        
        assert result == "done"

    def test_routing_function_returns_decision(self, registry):
        """Test routing returns decision from _internal."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        route_fn = builder.create_routing_function("main")
        
        state = {
            "response": {},
            "_internal": {"decision": "node_a"},
        }
        
        result = route_fn(state)
        
        assert result == "node_a"

    def test_routing_function_returns_done_for_invalid_decision(self, registry):
        """Test routing returns 'done' for invalid decision."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        route_fn = builder.create_routing_function("main")
        
        state = {
            "response": {},
            "_internal": {"decision": "invalid_node"},
        }
        
        result = route_fn(state)
        
        assert result == "done"


# =============================================================================
# build_graph_from_registry Tests
# =============================================================================

class TestBuildGraphFromRegistry:
    """Tests for build_graph_from_registry function."""

    @pytest.fixture
    def registry(self):
        """Create registry with test nodes."""
        reg = NodeRegistry()
        reg.register(SampleNodeA)
        reg.register(SampleNodeB)
        return reg

    def test_builds_state_graph(self, registry):
        """Test that function returns a StateGraph."""
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
        )
        
        assert isinstance(graph, StateGraph)

    def test_adds_supervisor_nodes(self, registry):
        """Test that supervisor nodes are added."""
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
        )
        
        # Check nodes exist in graph
        assert "main_supervisor" in graph.nodes

    def test_adds_worker_nodes(self, registry):
        """Test that worker nodes are added."""
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
        )
        
        assert "node_a" in graph.nodes
        assert "node_b" in graph.nodes

    def test_with_entrypoint(self, registry):
        """Test with custom entrypoint."""
        async def entry_node(state):
            return state
        
        def entry_route(state):
            return "main_supervisor"
        
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
            entrypoint=("entry", entry_node, entry_route),
        )
        
        assert "entry" in graph.nodes

    def test_with_llm_provider(self, registry):
        """Test with llm_provider."""
        mock_llm_provider = MagicMock(return_value=MagicMock())
        
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
            llm_provider=mock_llm_provider,
        )
        
        assert isinstance(graph, StateGraph)

    def test_with_dependency_provider(self, registry):
        """Test with dependency_provider."""
        mock_dep_provider = MagicMock(return_value={})
        
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
            dependency_provider=mock_dep_provider,
        )
        
        assert isinstance(graph, StateGraph)

    def test_with_state_class(self, registry):
        """Test with custom state class."""
        class CustomState(dict):
            pass
        
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
            state_class=CustomState,
        )
        
        assert isinstance(graph, StateGraph)

    def test_terminal_node_edges_to_end(self, registry):
        """Test that terminal nodes edge to END."""
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
        )
        
        # node_b is terminal, should edge to END
        edges = graph.edges
        # Check that node_b has an edge (to END)
        node_b_edges = [e for e in edges if e[0] == "node_b"]
        assert len(node_b_edges) > 0

    def test_non_terminal_node_edges_to_supervisor(self, registry):
        """Test that non-terminal nodes edge back to supervisor."""
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
        )
        
        # node_a is not terminal, should edge to supervisor
        edges = graph.edges
        node_a_edges = [e for e in edges if e[0] == "node_a"]
        assert len(node_a_edges) > 0

    def test_with_supervisor_factory(self, registry):
        """Test with custom supervisor_factory parameter."""
        from agent_contracts import GenericSupervisor
        
        def custom_context_builder(state, candidates):
            return {
                "slices": {"request", "response", "_internal", "custom"},
                "summary": "Custom context"
            }
        
        def supervisor_factory(name: str, llm):
            return GenericSupervisor(
                supervisor_name=name,
                llm=llm,
                registry=registry,
                context_builder=custom_context_builder,
            )
        
        mock_llm_provider = MagicMock(return_value=MagicMock())
        
        # Should not raise error
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
            llm_provider=mock_llm_provider,
            supervisor_factory=supervisor_factory,
        )
        
        assert isinstance(graph, StateGraph)
        assert "main_supervisor" in graph.nodes
