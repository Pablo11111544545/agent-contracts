# agent-contracts

Modular node architecture for LangGraph agents.

## Installation

```bash
pip install agent-contracts
# or from git
pip install git+https://github.com/your-org/agent-contracts.git
```

## Quick Start

```python
from agent_contracts import ModularNode, NodeContract, TriggerCondition
from langchain_openai import ChatOpenAI

class MyNode(ModularNode):
    CONTRACT = NodeContract(
        name="my_node",
        description="Custom processing node",
        reads=["request"],
        writes=["response"],
        requires_llm=True,
        supervisor="main",
    )

    async def execute(self, inputs):
        # Your logic here
        return NodeOutputs(response={"message": "Hello!"})
```

## Features

- **Contract-Driven**: Nodes declare their I/O and dependencies
- **Registry-Based**: Auto-build LangGraph from registered nodes
- **Generic Supervisor**: Rule-based + LLM fallback routing
- **Config System**: YAML-based configuration with Pydantic validation

## License

MIT
