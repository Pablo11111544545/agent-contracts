# agent-contracts

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

English | [日本語](README.ja.md)

**A modular, contract-driven node architecture for building LangGraph agents.**

`agent-contracts` provides a structured way to build AI agents using declarative contracts that define node I/O, dependencies, and routing rules. This enables automatic graph construction, type-safe state management, and flexible LLM-powered routing.

![Architecture Overview](images/overview.png)

---

## ✨ Features

- **📝 Contract-Driven Design**: Nodes declare their I/O, dependencies, and trigger conditions through `NodeContract`
- **🔧 Registry-Based Architecture**: Auto-build LangGraph from registered nodes without manual wiring
- **🧠 LLM-Driven Supervisor**: LLM makes routing decisions with rule-based hints and fallbacks
- **💬 Interactive Nodes**: Built-in base class for conversational agents with interview patterns
- **📊 Typed State Management**: Pydantic-based state slices with validation
- **⚙️ YAML Configuration**: Externalize settings with Pydantic validation

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

    async def execute(self, inputs: NodeInputs) -> NodeOutputs:
        request = inputs.get_slice("request")
        user_name = request.get("params", {}).get("name", "User")
        
        # Use LLM for greeting
        response = await self.llm.ainvoke(
            f"Generate a friendly greeting for {user_name}"
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
from agent_contracts.config import load_config, get_config

# Load from file
load_config("path/to/agent_config.yaml")

# Access config
config = get_config()
print(config.supervisor.max_iterations)
```

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

### State Management

```python
from agent_contracts import (
    BaseAgentState,
    BaseRequestSlice,
    BaseResponseSlice,
    get_slice,
    merge_slice_updates,
)
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔗 Links

- [GitHub Repository](https://github.com/yatarousan0227/agent-contracts)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
