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
from examples.interactive_tech_support.nodes.base_support_node import BaseSupportNode


class NetworkNode(BaseSupportNode):
    """Handles network-related support issues.

    Specializes in: WiFi connectivity, internet access, VPN, DNS,
    router configuration, and Ethernet issues.
    """

    SYSTEM_PROMPT = (
        "You are a network support specialist. "
        "Your goal is to help users troubleshoot internet and connectivity issues. "
        "Use the provided knowledge base articles to guide your response. "
        "Be concise, step-by-step, and empathetic."
    )

    CONTRACT = NodeContract(
        name="network_support",
        description="Handles network issues: WiFi, internet, connectivity, VPN, DNS",
        reads=["request", "support_context"],
        writes=["response", "support_context"],
        supervisor="tech_support",
        is_terminal=False,
        trigger_conditions=[
            # Rule-based routing via routing.category; LLM uses hints.
            TriggerCondition(
                priority=50,
                when={"routing.category": "network"},
                llm_hint=(
                    "User has a network/internet issue: WiFi, internet connection, "
                    "slow network, VPN, router, DNS, IP address problems"
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
        history = support_context.get("conversation_history", [])

        # Search knowledge base
        result = search_network_kb(message)
        
        # Decide response generation method
        if self.llm:
            response_message = await self._generate_llm_response(
                message, history, result
            )
        else:
            # Fallback
            if result:
                response_message = self._format_response(result)
            else:
                response_message = (
                    "I can help with network issues. "
                    "Could you provide more details about the specific network "
                    "problem you're experiencing? "
                    "Common issues: WiFi, internet connection, VPN, DNS."
                )

        response_data = {
            "title": result.get("title", "Network Support") if result else "Network Support",
            "steps": result.get("steps", []) if result else [],
            "follow_up": result.get("follow_up") if result else None,
            "category": "network",
            "issue_type": result.get("issue") if result else None,
        }

        # Update conversation history
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
