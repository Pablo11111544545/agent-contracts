"""Software specialist node for tech support."""

import sys

sys.path.insert(0, "src")

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
)

from examples.interactive_tech_support.knowledge.software_kb import search_software_kb


class SoftwareNode(ModularNode):
    """Handles software-related support issues.

    Specializes in: application crashes, errors, installations, updates,
    performance issues, malware, and browser problems.
    """

    CONTRACT = NodeContract(
        name="software_support",
        description=(
            "Handles software issues: crashes, errors, installation, "
            "updates, application problems"
        ),
        reads=["request", "support_context"],
        writes=["response", "support_context"],
        supervisor="tech_support",
        is_terminal=False,
        trigger_conditions=[
            # High priority: explicit software category
            TriggerCondition(
                priority=100,
                when={"request.category": "software"},
            ),
            # Medium priority: keyword detection
            TriggerCondition(
                priority=50,
                llm_hint=(
                    "User mentions software: crash, error, install, update, "
                    "application, program, freeze, slow, bug"
                ),
            ),
        ],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        """Process software support request.

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
        result = search_software_kb(message)

        if result:
            response_data = {
                "title": result.get("title", "Software Support"),
                "steps": result.get("steps", []),
                "follow_up": result.get("follow_up"),
                "category": "software",
                "issue_type": result.get("issue"),
            }
            response_message = self._format_response(result)
        else:
            response_data = {
                "title": "Software Support",
                "steps": [
                    "1. Restart the application",
                    "2. Check for updates",
                    "3. Clear cache and temporary files",
                    "4. Reinstall if necessary",
                ],
                "follow_up": "Can you provide more details about your software issue?",
                "category": "software",
            }
            response_message = (
                "I can help with software issues. "
                "Could you provide more details about the specific application "
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
                "node": "software_support",
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
        lines = [f"**{result.get('title', 'Software Support')}**", ""]
        lines.append("Try these steps:")

        for step in result.get("steps", []):
            lines.append(step)

        if result.get("follow_up"):
            lines.append("")
            lines.append(result.get("follow_up"))

        return "\n".join(lines)
