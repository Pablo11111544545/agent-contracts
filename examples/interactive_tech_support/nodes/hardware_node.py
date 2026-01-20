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


class HardwareNode(ModularNode):
    """Handles hardware-related support issues.

    Specializes in: printers, monitors, keyboards, mice, USB devices,
    power issues, and other physical hardware problems.
    """

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
            # High priority: explicit hardware category
            TriggerCondition(
                priority=100,
                when={"request.category": "hardware"},
            ),
            # Medium priority: keyword detection
            TriggerCondition(
                priority=50,
                llm_hint=(
                    "User mentions hardware: printer, monitor, keyboard, mouse, "
                    "USB, cable, screen, display, power, battery"
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

        # Search knowledge base
        result = search_hardware_kb(message)

        if result:
            response_data = {
                "title": result.get("title", "Hardware Support"),
                "steps": result.get("steps", []),
                "follow_up": result.get("follow_up"),
                "category": "hardware",
                "issue_type": result.get("issue"),
            }
            response_message = self._format_response(result)
        else:
            response_data = {
                "title": "Hardware Support",
                "steps": [
                    "1. Check all physical connections",
                    "2. Restart the device",
                    "3. Check for driver updates",
                    "4. Try the device on another computer",
                ],
                "follow_up": "Can you provide more details about your hardware issue?",
                "category": "hardware",
            }
            response_message = (
                "I can help with hardware issues. "
                "Could you provide more details about the specific hardware "
                "and the problem you're experiencing?"
            )

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
