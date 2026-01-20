"""Hardware specialist node for tech support."""

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
from examples.interactive_tech_support.nodes.base_support_node import BaseSupportNode


class HardwareNode(BaseSupportNode):
    """Handles hardware-related support issues.

    Specializes in: printers, monitors, keyboards, mice, USB devices,
    power issues, and other physical hardware problems.
    """

    SYSTEM_PROMPT = (
        "You are a hardware support specialist. "
        "Your goal is to help users troubleshoot physical device issues. "
        "Use the provided knowledge base articles to guide your response. "
        "Be concise, step-by-step, and empathetic."
    )

    CONTRACT = NodeContract(
        name="hardware_support",
        description=(
            "Handles hardware-related issues: printers, monitors, "
            "peripherals, physical components"
        ),
        reads=["request", "support_context"],
        writes=["response", "support_context"],
        supervisor="tech_support",
        is_terminal=False,
        trigger_conditions=[
            # Rule-based routing via routing.category; LLM uses hints.
            TriggerCondition(
                priority=50,
                when={"routing.category": "hardware"},
                llm_hint=(
                    "User has a hardware issue: printer, monitor, keyboard, mouse, "
                    "USB device, cable, screen, display, power, battery problems"
                ),
            ),
        ],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        """Process hardware support request.

        Args:
            inputs: Node inputs containing request and support_context.
            config: Optional configuration.

        Returns:
            Node outputs with response and updated support_context.
        """
        request = inputs.get_slice("request")
        support_context = inputs.get_slice("support_context") or {}

        message = request.get("message", "")
        history = support_context.get("conversation_history", [])

        # Search knowledge base
        result = search_hardware_kb(message)
        
        # Decide response generation method
        if self.llm:
            response_message = await self._generate_llm_response(
                message, history, result
            )
        else:
            # Fallback for no LLM
            if result:
                response_message = self._format_response(result)
            else:
                response_message = (
                    "I can help with hardware issues. "
                    "Could you provide more details about the specific device "
                    "and the problem you're experiencing? "
                    "Common issues I handle: printers, monitors, keyboards, power."
                )

        response_data = {
            "title": result.get("title", "Hardware Support") if result else "Hardware Support",
            "steps": result.get("steps", []) if result else [],
            "follow_up": result.get("follow_up") if result else None,
            "category": "hardware",
            "issue_type": result.get("issue") if result else None,
        }

        # Update conversation history
        history = support_context.get("conversation_history", [])
        history.append(
            {
                "role": "user",
                "content": message,
            }
        )
        history.append(
            {
                "role": "assistant",
                "content": response_message,
                "node": "hardware_support",
            }
        )

        return NodeOutputs(
            response={
                "response_type": "answer",
                "response_data": response_data,
                "response_message": response_message,
            },
            support_context={
                "conversation_history": history,
                "current_issue": result.get("issue") if result else None,
                "clarifications_count": support_context.get("clarifications_count", 0),
                "resolved": False,
            },
        )

    def _format_response(self, result: dict) -> str:
        """Format the knowledge base result into a readable response.

        Args:
            result: The knowledge base search result.

        Returns:
            Formatted response string.
        """
        lines = [f"**{result.get('title', 'Hardware Support')}**", ""]
        lines.append("Try these steps:")

        for step in result.get("steps", []):
            lines.append(step)

        if result.get("follow_up"):
            lines.append("")
            lines.append(result.get("follow_up"))

        return "\n".join(lines)
