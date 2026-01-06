"""agent_contracts - Modular node architecture for LangGraph agents.

This package provides:
- NodeContract: Declarative I/O contracts for nodes
- ModularNode: Base class for LangGraph nodes
- InteractiveNode: Base class for conversational nodes
- NodeRegistry: Registration and routing
- GenericSupervisor: LLM-driven routing with rule hints
- GraphBuilder: Automatic LangGraph construction
"""

from agent_contracts.contracts import (
    NodeContract,
    TriggerCondition,
    NodeInputs,
    NodeOutputs,
)
from agent_contracts.node import ModularNode, InteractiveNode
from agent_contracts.registry import NodeRegistry, get_node_registry, reset_registry
from agent_contracts.supervisor import GenericSupervisor, SupervisorDecision
from agent_contracts.graph_builder import GraphBuilder, build_graph_from_registry
from agent_contracts.state import (
    BaseAgentState,
    BaseRequestSlice,
    BaseResponseSlice,
    BaseInternalSlice,
    get_slice,
    merge_slice_updates,
)
from agent_contracts.router import BaseActionRouter

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Contracts
    "NodeContract",
    "TriggerCondition",
    "NodeInputs",
    "NodeOutputs",
    # Nodes
    "ModularNode",
    "InteractiveNode",
    # Registry
    "NodeRegistry",
    "get_node_registry",
    "reset_registry",
    # Supervisor
    "GenericSupervisor",
    "SupervisorDecision",
    # Graph
    "GraphBuilder",
    "build_graph_from_registry",
    # State
    "BaseAgentState",
    "BaseRequestSlice",
    "BaseResponseSlice",
    "BaseInternalSlice",
    "get_slice",
    "merge_slice_updates",
    # Router
    "BaseActionRouter",
]
