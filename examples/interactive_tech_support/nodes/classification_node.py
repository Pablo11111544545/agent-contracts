"""Classification node for tech support routing."""

import sys

sys.path.insert(0, "src")

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
)

from examples.interactive_tech_support.knowledge.hardware_kb import search_hardware_kb
from examples.interactive_tech_support.knowledge.software_kb import search_software_kb
from examples.interactive_tech_support.knowledge.network_kb import search_network_kb
from examples.interactive_tech_support.knowledge.faq_data import search_faq


class ClassificationNode(ModularNode):
    """Classifies incoming requests into support categories."""

    CONTRACT = NodeContract(
        name="classification",
        description=(
            "Internal: classify request into a routing category. "
            "Choose only when _internal.needs_classification is true."
        ),
        reads=["request", "routing", "_internal"],
        writes=["routing", "_internal"],
        supervisor="tech_support",
        is_terminal=False,
        trigger_conditions=[
            TriggerCondition(
                priority=90,
                when={"_internal.needs_classification": True},
                llm_hint=(
                    "Internal classifier. Use only when _internal.needs_classification "
                    "is true to set routing.category to hardware, software, network, "
                    "general, or clarification."
                ),
            ),
        ],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        """Classify the message and update routing hints."""
        request = inputs.get_slice("request") or {}
        message = request.get("message", "")

        category = None
        if message:
            if search_hardware_kb(message):
                category = "hardware"
            elif search_software_kb(message):
                category = "software"
            elif search_network_kb(message):
                category = "network"
            elif search_faq(message):
                category = "general"

        needs_clarification = category is None and self.llm is None

        return NodeOutputs(
            routing={"category": category},
            _internal={
                "needs_classification": False,
                "needs_clarification": needs_clarification,
            },
        )
