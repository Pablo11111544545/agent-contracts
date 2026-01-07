
import asyncio
from typing import Any, Annotated
from langgraph.graph import StateGraph, END
from agent_contracts import (
    NodeRegistry,
    NodeContract,
    TriggerCondition,
    ModularNode,
    NodeInputs,
    NodeOutputs,
    ContractVisualizer,
)

# =============================================================================
# Mock Nodes
# =============================================================================

class GreeterNode(ModularNode):
    CONTRACT = NodeContract(
        name="greeter",
        description="Greets the user",
        supervisor="main",
        requires_llm=True,
        reads=["request"],
        writes=["context", "response"],
        trigger_conditions=[
            TriggerCondition(priority=100, when={"request.action": "greet"}, llm_hint="Handle greeting")
        ]
    )
    async def execute(self, inputs: NodeInputs) -> NodeOutputs:
        return NodeOutputs(response={"msg": "Hello"})

class AnalyzerNode(ModularNode):
    CONTRACT = NodeContract(
        name="analyzer",
        description="Analyzes context",
        supervisor="main",
        requires_llm=True,
        reads=["context"],
        writes=["context"],
        trigger_conditions=[
            TriggerCondition(priority=50, when={"context.needs_analysis": "true"}, llm_hint="Run analysis")
        ]
    )
    async def execute(self, inputs: NodeInputs) -> NodeOutputs:
        return NodeOutputs(context={"analyzed": True})

class HelperNode(ModularNode):
    CONTRACT = NodeContract(
        name="helper",
        description="General helper",
        supervisor="main",
        requires_llm=True,
        reads=["request", "context"],
        writes=["task", "response"],
        trigger_conditions=[
            TriggerCondition(priority=10, llm_hint="General assistance")
        ]
    )
    async def execute(self, inputs: NodeInputs) -> NodeOutputs:
        return NodeOutputs(response={"msg": "Helping"})

class PlannerNode(ModularNode):
    CONTRACT = NodeContract(
        name="planner",
        description="Plans tasks",
        supervisor="task",
        requires_llm=True,
        reads=["request", "context", "task"],
        writes=["task"],
        trigger_conditions=[
            TriggerCondition(priority=80, when={"task.needs_planning": "true"}, llm_hint="Create plan")
        ]
    )
    async def execute(self, inputs: NodeInputs) -> NodeOutputs:
        return NodeOutputs(task={"plan": []})

class ExecutorNode(ModularNode):
    CONTRACT = NodeContract(
        name="executor",
        description="Executes tasks",
        supervisor="task",
        reads=["task"],
        writes=["task", "response"],
        trigger_conditions=[
            TriggerCondition(priority=50, when={"task.plan_ready": "true"}, llm_hint="Execute tasks")
        ]
    )
    async def execute(self, inputs: NodeInputs) -> NodeOutputs:
        return NodeOutputs(task={"done": True})

class ReporterNode(ModularNode):
    CONTRACT = NodeContract(
        name="reporter",
        description="Reports results",
        supervisor="task",
        requires_llm=True,
        is_terminal=True,
        reads=["task"],
        writes=["response"],
        trigger_conditions=[
            TriggerCondition(priority=30, when={"task.execution_done": "true"}, llm_hint="Generate report")
        ]
    )
    async def execute(self, inputs: NodeInputs) -> NodeOutputs:
        return NodeOutputs(response={"report": "Done"})

# =============================================================================
# Main
# =============================================================================

async def main():
    # 1. Register Nodes
    registry = NodeRegistry(valid_slices={"request", "context", "task", "response"})
    registry.register(GreeterNode)
    registry.register(AnalyzerNode)
    registry.register(HelperNode)
    registry.register(PlannerNode)
    registry.register(ExecutorNode)
    registry.register(ReporterNode)

    # 2. Build Mock Graph (Simplified flow for visualization)
    def reduce_ignore(a, b): return a
    builder = StateGraph(Annotated[dict, reduce_ignore]) # Allow parallel updates
    
    # Add nodes
    builder.add_node("greeter", lambda s: {})
    builder.add_node("helper", lambda s: {})
    builder.add_node("analyzer", lambda s: {})
    builder.add_node("planner", lambda s: {})
    builder.add_node("executor", lambda s: {})
    builder.add_node("reporter", lambda s: {})
    
    # Add supervisors (mock names)
    builder.add_node("main_supervisor", lambda s: {})
    builder.add_node("task_supervisor", lambda s: {})

    # Define edges to match sample flow roughly
    builder.set_entry_point("main_supervisor")
    builder.add_edge("main_supervisor", "greeter")
    builder.add_edge("main_supervisor", "helper")
    builder.add_edge("main_supervisor", "analyzer")
    
    builder.add_edge("greeter", "main_supervisor") # Loop back
    builder.add_edge("helper", "task_supervisor")  # Handoff
    builder.add_edge("analyzer", "main_supervisor")

    builder.add_edge("task_supervisor", "planner")
    builder.add_edge("task_supervisor", "executor")
    builder.add_edge("task_supervisor", "reporter")
    
    builder.add_edge("planner", "task_supervisor")
    builder.add_edge("executor", "task_supervisor")
    builder.add_edge("reporter", END)

    graph = builder.compile()

    # 3. Generate Docs
    visualizer = ContractVisualizer(registry, graph)
    doc = visualizer.generate_architecture_doc()

    with open("docs/ARCHITECTURE_SAMPLE.md", "w") as f:
        f.write(doc)
    
    print("Generated docs/ARCHITECTURE_SAMPLE.md")

if __name__ == "__main__":
    asyncio.run(main())
