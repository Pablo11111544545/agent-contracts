"""Clarification node for tech support."""

import sys

sys.path.insert(0, "src")

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
)


from examples.interactive_tech_support.nodes.base_support_node import BaseSupportNode


class ClarificationNode(BaseSupportNode):
    """Asks clarifying questions when the user's issue is unclear.

    This node is triggered when the system cannot determine
    the appropriate category or needs more information.
    """
    
    SYSTEM_PROMPT = (
        "You are a tech support assistant. "
        "The user's issue is unclear or vague. "
        "Ask a polite clarifying question to understand the problem better. "
        "Do not offer solutions yet, just ask for more details. "
        "Examples: 'What device are you using?', 'What error message do you see?'"
    )

    CONTRACT = NodeContract(
        name="clarification",
        description="Asks clarifying questions when the issue is unclear",
        reads=["request", "support_context", "_internal"],
        writes=["response", "support_context", "_internal"],
        supervisor="tech_support",
        is_terminal=False,
        trigger_conditions=[
            # [DEMO] High priority rule-based trigger
            # This demonstrates how to force a node execution via internal state flags
            TriggerCondition(
                priority=80,
                when={"_internal.needs_clarification": True},
                llm_hint=(
                    "User question is vague, ambiguous, or needs more information "
                    "to determine the correct support category"
                ),
            ),
        ],
    )

    # Clarification questions for different scenarios
    CLARIFICATION_QUESTIONS = {
        "device_type": {
            "question": (
                "To help you better, could you tell me what type of device "
                "you're having issues with?"
            ),
            "options": [
                "Desktop computer",
                "Laptop",
                "Printer",
                "Monitor/Display",
                "Network equipment (router/modem)",
                "Other peripheral",
            ],
        },
        "issue_type": {
            "question": "What kind of issue are you experiencing?",
            "options": [
                "Hardware/Physical problem",
                "Software/Application problem",
                "Network/Internet problem",
                "Other",
            ],
        },
        "os_type": {
            "question": "What operating system are you using?",
            "options": [
                "Windows 11",
                "Windows 10",
                "macOS",
                "Linux",
                "Chrome OS",
            ],
        },
        "timing": {
            "question": "When did this issue start?",
            "options": [
                "Just now",
                "After a recent update",
                "After installing something",
                "It's been happening for a while",
            ],
        },
    }

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        """Ask clarifying questions to better understand the issue.

        Args:
            inputs: Node inputs containing request, support_context, and _internal.
            config: Optional configuration.

        Returns:
            Node outputs with clarification questions.
        """
        request = inputs.get_slice("request")
        support_context = inputs.get_slice("support_context") or {}
        internal = inputs.get_slice("_internal") or {}

        message = request.get("message", "")

        # Track clarification count
        clarification_count = support_context.get("clarifications_count", 0) + 1

        # Determine which clarification to ask
        clarification_type = internal.get("clarification_type", "issue_type")
        
        # Decide response generation method
        if self.llm:
             # Use LLM to generate a context-aware question
            response_message = await self._generate_llm_response(
                message, 
                support_context.get("conversation_history", []),
                kb_result={"steps": ["Ask for specific details about the issue", "Identify if it is hardware, software, or network related"]}
            )
            
            # For API response structure, we still need some structured data
            # We'll use a generic "open" question type
            question = response_message
            options = ["I'll provide more details"] 
        else:
            # Fallback to fixed questions
            clarification = self.CLARIFICATION_QUESTIONS.get(
                clarification_type, self.CLARIFICATION_QUESTIONS["issue_type"]
            )
            question = clarification["question"]
            options = clarification["options"]
            
            options_text = "\n".join(f"  {i+1}. {opt}" for i, opt in enumerate(options))
            response_message = f"{question}\n\n{options_text}"

        response_data = {
            "title": "Let me help you better",
            "question": question,
            "options": options,
            "clarification_type": clarification_type,
            "category": "clarification",
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
                "node": "clarification",
            }
        )

        return NodeOutputs(
            response={
                "response_type": "question",
                "response_data": response_data,
                "response_message": response_message,
            },
            support_context={
                "conversation_history": history,
                "current_issue": support_context.get("current_issue"),
                "clarifications_count": clarification_count,
                "resolved": False,
            },
            _internal={
                "needs_clarification": False,
                "last_clarification_type": clarification_type,
            },
        )
