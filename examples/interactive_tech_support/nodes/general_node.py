"""General support node for tech support (FAQ handler)."""

import sys

sys.path.insert(0, "src")

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
)

from examples.interactive_tech_support.knowledge.faq_data import (
    search_faq,
    get_all_faq_topics,
)
from examples.interactive_tech_support.nodes.base_support_node import BaseSupportNode


class GeneralNode(BaseSupportNode):
    """Handles general tech questions and FAQ items.

    This is the fallback node for questions that don't match
    hardware, software, or network categories.
    """

    SYSTEM_PROMPT = (
        "You are a general tech support assistant. "
        "Your goal is to handle general inquiries and FAQ items. "
        "If you're unsure, suggest relevant topics or ask for clarification. "
        "Be helpful and friendly."
    )

    CONTRACT = NodeContract(
        name="general_support",
        description="Handles general questions and FAQ items",
        reads=["request", "support_context"],
        writes=["response"],
        supervisor="tech_support",
        is_terminal=True,
        trigger_conditions=[
            # Rule-based routing via routing.category; LLM uses hints.
            TriggerCondition(
                priority=20,
                when={"routing.category": "general"},
                llm_hint="General tech questions, FAQ items, or when other categories do not match",
            ),
        ],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        """Process general support request.

        Args:
            inputs: Node inputs containing request and support_context.
            config: Optional configuration.

        Returns:
            Node outputs with response.
        """
        request = inputs.get_slice("request")
        support_context = inputs.get_slice("support_context") or {}
        
        message = request.get("message", "")
        history = support_context.get("conversation_history", [])

        # Search FAQ data
        result = search_faq(message)
        
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
                # Provide list of available FAQ topics
                topics = get_all_faq_topics()
                topics_text = "\n".join(f"  - {topic}" for topic in topics[:5])
                response_message = (
                    "I'm not sure how to help with that specific question. "
                    "Here are some topics I can help with:\n\n"
                    f"{topics_text}\n\n"
                    "Or describe your tech issue and I'll try to help!"
                )

        if result:
            response_data = {
                "title": result.get("title", "General Support"),
                "content": result.get("content", ""),
                "question": result.get("question"),
                "category": "general",
            }
        else:
            topics = get_all_faq_topics()
            topics_text = "\n".join(f"  - {topic}" for topic in topics[:5])
            response_data = {
                "title": "General Support",
                "content": (
                    "I couldn't find a specific answer to your question. "
                    "Here are some common topics I can help with:\n\n"
                    f"{topics_text}\n\n"
                    "You can also ask about hardware, software, or network issues."
                ),
                "category": "general",
            }

        return NodeOutputs(
            response={
                "response_type": "answer",
                "response_data": response_data,
                "response_message": response_message,
            }
        )

    def _format_response(self, result: dict) -> str:
        """Format the FAQ result into a readable response.

        Args:
            result: The FAQ search result.

        Returns:
            Formatted response string.
        """
        lines = [f"**{result.get('title', 'General Support')}**", ""]

        content = result.get("content", "")
        if content:
            lines.append(content)

        return "\n".join(lines)
