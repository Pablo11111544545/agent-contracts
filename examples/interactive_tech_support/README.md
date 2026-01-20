# Interactive Tech Support Demo

A comprehensive example demonstrating agent-contracts for building a multi-node tech support assistant with interactive CUI and optional LLM integration.

## Overview

This example creates a **Tech Support Assistant** that:
- Routes user questions to specialized support agents (Hardware, Software, Network, General)
- Demonstrates both rule-based and LLM-based routing
- Works standalone with hardcoded FAQ/knowledge data
- Provides an interactive CUI with LLM provider configuration
- Shows clear benefits of contract-driven development

## Quick Start

```bash
# From the project root
python -m examples.interactive_tech_support
```

## Features

### Specialist Nodes

| Node | Category | Description |
|------|----------|-------------|
| `HardwareNode` | Hardware | Handles printer, monitor, keyboard, mouse, USB, power issues |
| `SoftwareNode` | Software | Handles crashes, errors, installations, updates, malware |
| `NetworkNode` | Network | Handles WiFi, internet, VPN, DNS, router issues |
| `GeneralNode` | FAQ | Handles general tech questions and FAQ items |
| `ClarificationNode` | Clarification | Asks clarifying questions when the issue is unclear |

### Routing

The assistant uses a two-tier routing system:

1. **Rule-based routing**: Keywords in the user's message are matched against predefined patterns
2. **LLM-based routing**: When rules don't match, an optional LLM can make semantic routing decisions

### CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/setup` | Configure LLM provider |
| `/status` | Show current configuration |
| `/debug` | Toggle debug mode (show routing info) |
| `/clear` | Clear conversation history |
| `/exit` | Exit the application |

## Architecture

```
examples/interactive_tech_support/
├── __init__.py
├── __main__.py           # Entry point
├── main.py               # Main application runner
├── README.md
│
├── config/
│   ├── __init__.py
│   ├── settings.yaml     # Framework configuration
│   ├── llm_providers.yaml # LLM provider definitions
│   └── loader.py         # Configuration loader
│
├── nodes/
│   ├── __init__.py
│   ├── hardware_node.py  # Hardware specialist
│   ├── software_node.py  # Software specialist
│   ├── network_node.py   # Network specialist
│   ├── general_node.py   # General/FAQ handler
│   └── clarification_node.py # Clarifying questions
│
├── knowledge/
│   ├── __init__.py
│   ├── hardware_kb.py    # Hardware troubleshooting data
│   ├── software_kb.py    # Software troubleshooting data
│   ├── network_kb.py     # Network troubleshooting data
│   └── faq_data.py       # General FAQ data
│
├── cli/
│   ├── __init__.py
│   ├── app.py            # Main CLI application
│   ├── setup_wizard.py   # LLM setup wizard
│   └── display.py        # Display helpers
│
└── utils/
    ├── __init__.py
    └── llm_factory.py    # LLM provider factory
```

## LLM Provider Support

The example supports multiple LLM providers:

| Provider | Required Package | Environment Variable |
|----------|-----------------|---------------------|
| OpenAI | `langchain-openai` | `OPENAI_API_KEY` |
| Azure OpenAI | `langchain-openai` | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` |
| Anthropic | `langchain-anthropic` | `ANTHROPIC_API_KEY` |
| Google AI | `langchain-google-genai` | `GOOGLE_API_KEY` |
| Ollama | `langchain-ollama` | (local, no API key needed) |

### Installing LLM Providers

```bash
# For OpenAI
pip install langchain-openai

# For Anthropic
pip install langchain-anthropic

# For Google AI
pip install langchain-google-genai

# For Ollama
pip install langchain-ollama
```

## Example Session

```
================================================================
              Tech Support Assistant
           Powered by agent-contracts
================================================================

Welcome! I can help you with:
  * Hardware issues (printers, monitors, peripherals)
  * Software problems (crashes, errors, installations)
  * Network troubles (WiFi, internet, connectivity)

LLM Status: Not configured (rule-based routing)

Type /help for commands, or describe your issue.
------------------------------------------------------------
You: My wifi keeps disconnecting

============================================================
[NET] WiFi Keeps Disconnecting
Routed via: keyword match (wifi)
------------------------------------------------------------

Try these steps:
  1. Check WiFi signal strength
  2. Update wireless network drivers
  3. Disable power saving for WiFi adapter
  4. Reset network settings
  5. Check for router overheating
  6. Try a different WiFi channel

>> Is your WiFi connection stable now?
============================================================

You: /exit

Thank you for using Tech Support Assistant!
Goodbye!
```

## What This Example Demonstrates

| Feature | Demonstration |
|---------|--------------|
| **Contracts** | Clear I/O definitions for each specialist node |
| **Routing** | Both rule-based (keywords) and LLM-based (semantic) |
| **Modularity** | Self-contained nodes, easy to add new specialists |
| **Configuration** | YAML-based settings, LLM provider flexibility |
| **Observability** | Debug mode shows routing decisions |
| **Standalone** | Works without LLM using hardcoded knowledge base |
| **Interactive** | Full CUI with setup wizard and commands |

## Extending the Example

### Adding a New Specialist Node

1. Create a new knowledge base in `knowledge/`
2. Create a new node in `nodes/` with a `NodeContract`
3. Register the node in `cli/app.py`

### Adding Knowledge Base Entries

Add entries to the appropriate knowledge base file:
- `knowledge/hardware_kb.py` for hardware issues
- `knowledge/software_kb.py` for software issues
- `knowledge/network_kb.py` for network issues
- `knowledge/faq_data.py` for general FAQ items
