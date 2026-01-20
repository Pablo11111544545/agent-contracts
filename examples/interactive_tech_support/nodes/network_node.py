"""Network specialist node for tech support."""

import sys

sys.path.insert(0, "src")

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
)

from examples.interactive_tech_support.knowledge.network_kb import search_network_kb


class NetworkNode(ModularNode):
    """Handles network-related support issues.

    Specializes in: WiFi connectivity, internet access, VPN, DNS,
    router configuration, and Ethernet issues.
    """

    CONTRACT = NodeContract(
        name="network_support",
        description="Handles network issues: WiFi, internet, connectivity, VPN, DNS",
        reads=["request", "support_context"],
        writes=["response", "support_context"],
        supervisor="tech_support",
        is_terminal=False,
        trigger_conditions=[
            # High priority: explicit network category
            TriggerCondition(
                priority=100,
                when={"request.category": "network"},
            ),
            # Medium priority: keyword detection
            TriggerCondition(
                priority=50,
                llm_hint=(
                    "User mentions network: wifi, internet, connection, "
                    "slow network, VPN, router, DNS, IP address"
                ),
            ),
        ],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        """Process network support request.

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
        result = search_network_kb(message)

        if result:
            response_data = {
                "title": result.get("title", "Network Support"),
                "steps": result.get("steps", []),
                "follow_up": result.get("follow_up"),
                "category": "network",
                "issue_type": result.get("issue"),
            }
            response_message = self._format_response(result)
        else:
            response_data = {
                "title": "Network Support",
                "steps": [
                    "1. Check if WiFi/Ethernet is connected",
                    "2. Restart your router/modem",
                    "3. Check cable connections",
                    "4. Try accessing different websites",
                ],
                "follow_up": "Can you provide more details about your network issue?",
                "category": "network",
            }
            response_message = (
                "I can help with network issues. "
                "Could you provide more details about the specific network "
                "problem you're experiencing?"
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
                "node": "network_support",
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
        lines = [f"**{result.get('title', 'Network Support')}**", ""]
        lines.append("Try these steps:")

        for step in result.get("steps", []):
            lines.append(step)

        if result.get("follow_up"):
            lines.append("")
            lines.append(result.get("follow_up"))

        return "\n".join(lines)
