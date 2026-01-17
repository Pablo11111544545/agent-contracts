# Getting Started

> Build your first agent in 10 minutes

---

## Prerequisites

- Python 3.11+
- Basic understanding of LangGraph

---

## Installation

```bash
# From PyPI
pip install agent-contracts

# Or from GitHub
pip install git+https://github.com/yatarousan0227/agent-contracts.git
```

---

## Your First Node

Create a simple node that handles a greeting request:

```python
# my_agent.py
from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
)


class GreetingNode(ModularNode):
    """A simple greeting node."""
    
    CONTRACT = NodeContract(
        name="greeting",
        description="Generates a personalized greeting",
        reads=["request"],           # Read from 'request' slice
        writes=["response"],         # Write to 'response' slice
        supervisor="main",           # Belongs to 'main' supervisor
        is_terminal=True,            # End the flow after this node
        trigger_conditions=[
            TriggerCondition(
                priority=10,
                when={"request.action": "greet"},
                llm_hint="Use when user wants a greeting",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        # Get data from request slice
        request = inputs.get_slice("request")
        name = request.get("params", {}).get("name", "World")
        
        # Return response
        return NodeOutputs(
            response={
                "response_type": "greeting",
                "response_message": f"Hello, {name}!",
            }
        )
```

---

## Your First Graph

Register the node and build a LangGraph:

```python
from agent_contracts import BaseAgentState, get_node_registry, build_graph_from_registry
from langchain_openai import ChatOpenAI


# Get the global registry
registry = get_node_registry()

# Register your node
registry.register(GreetingNode)

# Build the graph (LLM is optional for simple routing)
llm = ChatOpenAI(model="gpt-4")
graph = build_graph_from_registry(
    registry=registry,
    llm=llm,
    supervisors=["main"],
    state_class=BaseAgentState,
)

# Set entrypoint and compile for execution
graph.set_entry_point("main_supervisor")
compiled = graph.compile()
```

---

## Running the Agent

```python
import asyncio


async def main():
    result = await compiled.ainvoke({
        "request": {
            "action": "greet",
            "params": {"name": "Alice"},
        },
    })
    
    print(result["response"])
    # Output: {'response_type': 'greeting', 'response_message': 'Hello, Alice!'}


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Adding Validation

Before running, validate your contracts:

```python
from agent_contracts import ContractValidator

validator = ContractValidator(registry)
result = validator.validate()

if result.has_errors:
    print(result)
    exit(1)

print("✅ Contracts validated!")
```

---

## Next Steps

- 📚 [Core Concepts](core_concepts.md) - Understand the architecture
- 🧰 [CLI](cli.md) - Validate, visualize, and diff contracts
- 🎯 [Best Practices](best_practices.md) - Design patterns and tips
- 🐛 [Troubleshooting](troubleshooting.md) - Common issues and solutions
- 📦 Examples - See `examples/05_backend_runtime.py` for a backend runtime flow
