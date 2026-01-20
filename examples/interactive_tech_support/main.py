#!/usr/bin/env python3
"""
Interactive Tech Support Demo
=============================

A comprehensive example demonstrating agent-contracts for building
a multi-node tech support assistant with interactive CUI and
optional LLM integration.

This example demonstrates:
- NodeContract definition for multiple specialist nodes
- TriggerCondition with priority and LLM hints
- GenericSupervisor for routing decisions
- Both rule-based and LLM-based routing
- Interactive CLI with setup wizard

Run with:
    python -m examples.interactive_tech_support

Or from the examples directory:
    cd examples/interactive_tech_support
    python main.py
"""

import sys

# Ensure src is in path
sys.path.insert(0, "src")

from examples.interactive_tech_support.cli.app import TechSupportCLI


def main() -> None:
    """Run the interactive tech support demo."""
    try:
        cli = TechSupportCLI()
        cli.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
