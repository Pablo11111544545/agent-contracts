#!/usr/bin/env python3
"""
Example: Multi-Step Workflow
============================

Demonstrates a sequential workflow pattern where nodes
pass control using internal flags.

This example shows:
- Using _internal flags for workflow state
- Sequential node execution via Supervisor
- Data accumulation across steps

Workflow:
1. DataCollector → collects input data
2. Processor → transforms the data  
3. Reporter → generates final output

Run with:
    python examples/04_multi_step_workflow.py
"""

import asyncio
import sys
sys.path.insert(0, "src")

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
    NodeRegistry,
    GenericSupervisor,
)


# =============================================================================
# State Slices
# =============================================================================

# The 'workflow' slice accumulates data across steps:
# {
#     "input_data": [...],      # Raw input
#     "processed_data": [...],  # After processing
#     "report": str,            # Final report
# }


# =============================================================================
# Workflow Nodes
# =============================================================================

class DataCollectorNode(ModularNode):
    """Step 1: Collects input data."""
    
    CONTRACT = NodeContract(
        name="data_collector",
        description="Collects and validates input data",
        reads=["request", "workflow"],
        writes=["workflow", "_internal"],
        supervisor="pipeline",
        trigger_conditions=[
            TriggerCondition(
                priority=100,
                when={"_internal.step": "collect"},
                llm_hint="First step - collect data",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        request = inputs.get_slice("request")
        workflow = inputs.get_slice("workflow") or {}
        raw_items = request.get("items", [])
        
        print(f"  📥 DataCollector: Received {len(raw_items)} items")
        
        return NodeOutputs(
            workflow={
                **workflow,
                "input_data": raw_items,
            },
            _internal={
                "step": "process",  # Signal next step
            },
        )


class ProcessorNode(ModularNode):
    """Step 2: Processes the collected data."""
    
    CONTRACT = NodeContract(
        name="processor",
        description="Transforms and enriches data",
        reads=["workflow"],
        writes=["workflow", "_internal"],
        supervisor="pipeline",
        trigger_conditions=[
            TriggerCondition(
                priority=100,
                when={"_internal.step": "process"},
                llm_hint="Second step - process data",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        workflow = inputs.get_slice("workflow") or {}
        input_data = workflow.get("input_data", [])
        
        # Transform: uppercase all strings
        processed = [item.upper() if isinstance(item, str) else item for item in input_data]
        
        print(f"  ⚙️ Processor: Transformed {len(processed)} items")
        
        return NodeOutputs(
            workflow={
                **workflow,
                "processed_data": processed,
            },
            _internal={
                "step": "report",  # Signal next step
            },
        )


class ReporterNode(ModularNode):
    """Step 3: Generates the final report."""
    
    CONTRACT = NodeContract(
        name="reporter",
        description="Generates summary report",
        reads=["workflow"],
        writes=["workflow", "response"],
        supervisor="pipeline",
        is_terminal=True,
        trigger_conditions=[
            TriggerCondition(
                priority=100,
                when={"_internal.step": "report"},
                llm_hint="Final step - generate report",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        workflow = inputs.get_slice("workflow") or {}
        processed_data = workflow.get("processed_data", [])
        
        report = f"Processed {len(processed_data)} items: {', '.join(map(str, processed_data))}"
        
        print(f"  📊 Reporter: Generated report")
        
        return NodeOutputs(
            workflow={
                **workflow,
                "report": report,
            },
            response={
                "response_type": "report",
                "response_data": {
                    "report": report,
                    "item_count": len(processed_data),
                },
            },
        )


# =============================================================================
# Demo
# =============================================================================

async def run_workflow(items: list):
    """Run the workflow with given items."""
    
    # Setup registry with custom 'workflow' slice
    registry = NodeRegistry()
    registry.add_valid_slice("workflow")
    registry.register(DataCollectorNode)
    registry.register(ProcessorNode)
    registry.register(ReporterNode)
    
    # Create supervisor
    supervisor = GenericSupervisor(
        supervisor_name="pipeline",
        llm=None,
        registry=registry,
        max_iterations=10,
        terminal_response_types={"report"},
    )
    
    # Node instances
    nodes = {
        "data_collector": DataCollectorNode(llm=None),
        "processor": ProcessorNode(llm=None),
        "reporter": ReporterNode(llm=None),
    }
    
    # Initial state
    state = {
        "request": {"items": items},
        "workflow": {},
        "response": {},
        "_internal": {"step": "collect"},  # Start at collect step
    }
    
    # Execute workflow
    max_steps = 5
    for step in range(max_steps):
        # Get routing decision
        decision = await supervisor.decide_with_trace(state)
        
        if decision.selected_node == "done":
            break
            
        # Execute selected node
        node = nodes.get(decision.selected_node)
        if not node:
            print(f"⚠️ Unknown node: {decision.selected_node}")
            break
            
        inputs = NodeInputs(
            request=state["request"],
            workflow=state["workflow"],
        )
        outputs = await node.execute(inputs)
        
        # Update state with output slices
        for key, value in outputs.to_state_updates().items():
            if key in state:
                state[key] = {**state[key], **value}
            else:
                state[key] = value
        
        # Check if terminal
        if node.CONTRACT.is_terminal:
            break
    
    return state


async def main():
    """Demo the multi-step workflow."""
    print()
    print("🔄 Multi-Step Workflow Demo")
    print("=" * 50)
    print()
    print("Workflow: DataCollector → Processor → Reporter")
    print()
    
    # Run with sample data
    items = ["apple", "banana", "cherry"]
    print(f"📨 Input: {items}")
    print()
    print("Running workflow...")
    
    result = await run_workflow(items)
    
    print()
    response = result.get("response", {})
    report = response.get("response_data", {}).get("report", "No report")
    print(f"📋 Final Report: {report}")
    print()
    
    # Show the workflow state
    workflow = result.get("workflow", {})
    print("Workflow State:")
    print(f"  - input_data: {workflow.get('input_data')}")
    print(f"  - processed_data: {workflow.get('processed_data')}")
    print(f"  - report: {workflow.get('report')}")
    print()
    
    print("=" * 50)
    print("✅ Workflow completed!")
    print()


if __name__ == "__main__":
    asyncio.run(main())
