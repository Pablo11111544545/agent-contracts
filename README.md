# agent-contracts

[![PyPI version](https://img.shields.io/pypi/v/agent-contracts.svg)](https://pypi.org/project/agent-contracts/)
[![PyPI downloads](https://img.shields.io/pypi/dm/agent-contracts.svg)](https://pypi.org/project/agent-contracts/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![CI](https://github.com/yatarousan0227/agent-contracts/actions/workflows/ci.yml/badge.svg)](https://github.com/yatarousan0227/agent-contracts/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-GitHub_Pages-blue.svg)](https://yatarousan0227.github.io/agent-contracts/)

English | [日本語](README.ja.md)

**A modular, contract-driven node architecture for building LangGraph agents.**

`agent-contracts` provides a structured way to build AI agents using declarative contracts that define node I/O, dependencies, and routing rules. This enables automatic graph construction, type-safe state management, and flexible LLM-powered routing.

![Architecture Overview](images/overview.png)

📘 **Full Documentation**: [https://yatarousan0227.github.io/agent-contracts/](https://yatarousan0227.github.io/agent-contracts/)


---

## ✨ Features

- **📝 Contract-Driven Design**: Nodes declare their I/O, dependencies, and trigger conditions through `NodeContract`
- **🔧 Registry-Based Architecture**: Auto-build LangGraph from registered nodes without manual wiring
- **🧠 LLM-Driven Supervisor**: LLM makes routing decisions with rule-based hints and fallbacks
- **💬 Interactive Nodes**: Built-in base class for conversational agents with interview patterns
- **📊 Typed State Management**: Pydantic-based state slices with validation
- **🔒 StateAccessor Pattern**: Type-safe, immutable state access with IDE autocompletion
- **🔄 Runtime Layer**: Unified execution engine with hooks, session management, and streaming
- **⚙️ YAML Configuration**: Externalize settings with Pydantic validation
- **🏗️ Architecture Visualization**: Generate comprehensive architecture docs from contracts

---

## 📦 Installation

```bash
pip install agent-contracts

# or from git
pip install git+https://github.com/yatarousan0227/agent-contracts.git
```

### Requirements

- Python 3.11+
- LangGraph >= 0.2.0
- LangChain Core >= 0.3.0
- Pydantic >= 2.0.0

---

## 🚀 Quick Start

### 1. Define a Node with Contract

```python
from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition

class GreetingNode(ModularNode):
    CONTRACT = NodeContract(
        name="greeting",
        description="Generates a personalized greeting",
        reads=["request"],
        writes=["response"],
        requires_llm=True,
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                when={"request.action": "greet"},
                priority=10,
            )
        ],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        request = inputs.get_slice("request")
        user_name = request.get("params", {}).get("name", "User")
        
        # Use LLM for greeting (pass config for tracing)
        response = await self.llm.ainvoke(
            f"Generate a friendly greeting for {user_name}",
            config=config,
        )
        
        return NodeOutputs(
            response={
                "response_type": "greeting",
                "response_data": {"message": response.content},
            }
        )
```

### 2. Register and Build Graph

```python
from agent_contracts import get_node_registry, build_graph_from_registry
from langchain_openai import ChatOpenAI

# Get the global registry
registry = get_node_registry()

# Register your node
registry.register(GreetingNode)

# Build the LangGraph
llm = ChatOpenAI(model="gpt-4")
graph = build_graph_from_registry(
    registry=registry,
    llm=llm,
    supervisors=["main"],
)
compiled = graph.compile()

# Run the graph
result = await compiled.ainvoke({
    "request": {
        "action": "greet",
        "params": {"name": "Alice"}
    },
})
```

---

## 🏗️ Core Concepts

### NodeContract

`NodeContract` is the heart of the library. It declares everything about a node:

```python
NodeContract(
    # Identification
    name="my_node",                    # Unique node identifier
    description="What this node does", # Human-readable description
    
    # I/O Definition (by state slice)
    reads=["request", "context"],      # State slices this node reads
    writes=["response"],               # State slices this node writes
    
    # Dependencies
    requires_llm=True,                 # Whether LLM is required
    services=["db_service"],           # Required service names
    
    # Routing
    supervisor="main",                 # Which supervisor manages this node
    trigger_conditions=[...],          # When to trigger this node
    is_terminal=False,                 # Whether to END after execution
)
```

### TriggerCondition

Define when a node should be selected by the supervisor:

```python
TriggerCondition(
    priority=10,                           # Higher = evaluated first
    when={"request.action": "search"},     # Rule-based matching
    when_not={"response.done": True},      # Negative matching
    llm_hint="Use for product searches",   # LLM routing hint
)
```

### GenericSupervisor

The supervisor orchestrates node selection:

1. **Immediate Rules**: Check for terminal states
2. **Explicit Routing**: Return answers to question-owning nodes
3. **Rule-Based Hints**: Collect candidates from trigger conditions
4. **LLM Decision**: LLM makes final decision using rule hints
5. **Fallback**: Use top rule candidate if LLM unavailable

```python
from agent_contracts import GenericSupervisor

supervisor = GenericSupervisor(
    supervisor_name="main",
    llm=llm,
    max_iterations=10,
)
```

### InteractiveNode

For conversational agents, extend `InteractiveNode`:

```python
from agent_contracts import InteractiveNode

class InterviewNode(InteractiveNode):
    CONTRACT = NodeContract(...)
    
    def prepare_context(self, inputs):
        """Extract context from inputs."""
        return {"interview_state": inputs.get_slice("interview")}
    
    def check_completion(self, context, inputs):
        """Check if interview is complete."""
        return context["interview_state"].get("complete", False)
    
    async def process_answer(self, context, inputs):
        """Process user's answer."""
        # Handle the answer
        return True
    
    async def generate_question(self, context, inputs):
        """Generate next question."""
        return NodeOutputs(response={"question": "..."})
```

---

## ⚙️ Configuration

Create `agent_config.yaml` in your project:

```yaml
supervisor:
  max_iterations: 10

response_types:
  terminal_states:
    - interview
    - proposals
    - error

interview:
  my_interviewer:
    max_turns: 10
    max_questions: 5
```

Load configuration:

```python
from agent_contracts.config import load_config, set_config, get_config

# Load from file and set as global config
config = load_config("path/to/agent_config.yaml")
set_config(config)

# Access config anywhere
config = get_config()
print(config.supervisor.max_iterations)
```

---

---
 
 ## 🔍 Observability (LangSmith)
 
 `agent-contracts` is fully integrated with [LangSmith](https://smith.langchain.com/) for tracing and debugging.
 
 ### 1. Setup Environment Variables
 
 ```bash
 export LANGCHAIN_TRACING_V2=true
 export LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
 export LANGCHAIN_API_KEY="<your-api-key>"
 export LANGCHAIN_PROJECT="my-agent-project"
 ```
 
 ### 2. Automatic Tracing
 
 Just running the graph will automatically stream traces to LangSmith. The framework adds rich metadata to help you debug:
 
 - **Supervisors**: Shows iteration count, decision reasoning, and candidate rules.
 - **Nodes**: Shows execution time, input/output slices, and node type.
 
 ---
 
 ## 🏗️ Architecture Visualization

Generate comprehensive architecture documentation from your registered contracts:

```python
from agent_contracts import ContractVisualizer, get_node_registry

registry = get_node_registry()
# ... register your nodes ...
# ... build your graph ...
# compiled_graph = graph.compile()

# Pass the graph to visualize the LangGraph flow
visualizer = ContractVisualizer(registry, graph=compiled_graph)
doc = visualizer.generate_architecture_doc()

with open("ARCHITECTURE.md", "w") as f:
    f.write(doc)
```

### Generated Sections

The generated document includes:

| Section | Description |
|---------|-------------|
| **📦 State Slices** | All slices with readers/writers + ER diagram |
| **🔗 LangGraph Node Flow** | Mermaid visualization of the compiled LangGraph |
| **🎯 System Hierarchy** | Supervisor-Node structure with Mermaid flowchart |
| **🔀 Data Flow** | Node dependencies via shared slices |
| **⚡ Trigger Hierarchy** | Priority-ordered triggers (🔴 high → 🟢 low) |
| **📚 Nodes Reference** | Complete node details table |

### Individual Sections

You can also generate sections individually:

```python
# LangGraph flow
print(visualizer.generate_langgraph_flow())

# State slices documentation
print(visualizer.generate_state_slices_section())

# Hierarchy diagram
print(visualizer.generate_hierarchy_diagram())

# Data flow
print(visualizer.generate_dataflow_diagram())

# Trigger hierarchy
print(visualizer.generate_trigger_hierarchy())

# Nodes reference table
print(visualizer.generate_nodes_reference())
```

See [ARCHITECTURE_SAMPLE.md](docs/ARCHITECTURE_SAMPLE.md) for example output.

---
 
 ## 📚 API Reference

### Main Exports

| Export | Description |
|--------|-------------|
| `ModularNode` | Base class for all nodes |
| `InteractiveNode` | Base class for conversational nodes |
| `NodeContract` | Node I/O contract definition |
| `TriggerCondition` | Trigger condition for routing |
| `NodeInputs` / `NodeOutputs` | Typed I/O containers |
| `NodeRegistry` | Node registration and discovery |
| `GenericSupervisor` | LLM-driven routing supervisor |
| `GraphBuilder` | Automatic LangGraph construction |
| `BaseAgentState` | Base state class with slices |
| `ContractVisualizer` | Architecture document generator |

### Runtime Layer

| Export | Description |
|--------|-------------|
| `AgentRuntime` | Unified execution engine with lifecycle hooks |
| `StreamingRuntime` | Node-by-node streaming for SSE |
| `RequestContext` | Execution request container |
| `ExecutionResult` | Execution result with response |
| `RuntimeHooks` | Protocol for customization hooks |
| `SessionStore` | Protocol for session persistence |
| `InMemorySessionStore` | In-memory session store for dev/testing |

### StateAccessor Pattern

Type-safe, immutable state access:

```python
from agent_contracts import (
    StateAccessor,
    Internal,
    Request,
    Response,
    reset_response,
    increment_turn,
)

# Read state
count = Internal.turn_count.get(state)

# Write state (immutable - returns new state)
state = Internal.turn_count.set(state, 5)
state = reset_response(state)
```

### State Operations

```python
from agent_contracts.runtime import (
    create_base_state,
    merge_session,
    reset_internal_flags,
    ensure_slices,
    update_slice,
    get_nested,
)

# Create initial state
state = create_base_state(session_id="abc", action="answer")

# Merge session data
state = merge_session(state, session_data, ["interview", "shopping"])

# Update slice
state = update_slice(state, "interview", question_count=5)
```

---

## 🔄 Runtime Layer

For production applications, use the Runtime Layer for unified execution:

### AgentRuntime

```python
from agent_contracts import AgentRuntime, RequestContext, InMemorySessionStore

runtime = AgentRuntime(
    graph=compiled_graph,
    session_store=InMemorySessionStore(),
)

result = await runtime.execute(RequestContext(
    session_id="abc123",
    action="answer",
    message="I like casual style",
    resume_session=True,
))

print(result.response_type)  # "interview", "proposals", etc.
print(result.response_data)  # Response payload
```

### StreamingRuntime (SSE)

```python
from agent_contracts.runtime import StreamingRuntime, NodeExecutor

runtime = (
    StreamingRuntime()
    .add_node("search", search_node, "Searching...")
    .add_node("stylist", stylist_node, "Generating recommendations...")
)

async for event in runtime.stream(request):
    yield event.to_sse()
```

### Custom Hooks & Session Store

Implement protocols for your application:

```python
from agent_contracts import RuntimeHooks, SessionStore

class MySessionStore(SessionStore):
    async def load(self, session_id: str) -> dict | None:
        return await self.redis.get(session_id)
    
    async def save(self, session_id: str, data: dict, ttl: int = 3600):
        await self.redis.setex(session_id, ttl, data)
    
    async def delete(self, session_id: str):
        await self.redis.delete(session_id)

class MyHooks(RuntimeHooks):
    async def prepare_state(self, state, request):
        # Normalize state before execution
        return state
    
    async def after_execution(self, state, result):
        # Persist session, log, etc.
        pass
```

## 📖 Examples

| Example | Description |
|---------|-------------|
| [01_contract_validation.py](examples/01_contract_validation.py) | Static contract validation demo |
| [02_routing_explain.py](examples/02_routing_explain.py) | Traceable routing decisions demo |
| [03_simple_chatbot.py](examples/03_simple_chatbot.py) | Simple 3-node chatbot |
| [04_multi_step_workflow.py](examples/04_multi_step_workflow.py) | Multi-step workflow pattern |

Run examples:

```bash
python examples/01_contract_validation.py
python examples/02_routing_explain.py
python examples/03_simple_chatbot.py
python examples/04_multi_step_workflow.py
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting_started.md) | First steps with agent-contracts |
| [Core Concepts](docs/core_concepts.md) | Deep dive into the architecture |
| [Best Practices](docs/best_practices.md) | Design patterns and tips |
| [Troubleshooting](docs/troubleshooting.md) | Common issues and solutions |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the Mozilla Public License 2.0 (MPL-2.0) - see the [LICENSE](LICENSE) file for details.

> **Why MPL 2.0?** We chose MPL 2.0 to encourage community contributions while keeping the library easy to integrate. Any improvements to `agent-contracts` core files must be shared back, but your proprietary nodes and extensions remain yours.

---

## 🔗 Links

- [GitHub Repository](https://github.com/yatarousan0227/agent-contracts)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
