"""Base class for support nodes with LLM integration."""

import sys
from typing import Any

from agent_contracts import ModularNode, NodeInputs, NodeOutputs
from langchain_core.messages import HumanMessage, SystemMessage


class BaseSupportNode(ModularNode):
    """Base class for support nodes with LLM integration.
    
    Provides common functionality for:
    1. Generating LLM responses using conversation history
    2. Fallback to knowledge base search when no LLM is available
    """
    
    SYSTEM_PROMPT: str = "You are a helpful tech support assistant."
    
    async def _generate_llm_response(
        self, 
        message: str, 
        history: list[dict],
        kb_result: dict | None = None,
    ) -> str:
        """Generate response using LLM with conversation context.
        
        Args:
            message: Current user message.
            history: Conversation history.
            kb_result: Optional knowledge base search result to use as context.
            
        Returns:
            Generated response string.
        """
        if not self.llm:
            return "I apologize, but I cannot generate a response at this time."
            
        # Build messages
        messages = [SystemMessage(content=self.SYSTEM_PROMPT)]
        
        # Add relevant context from KB if available
        if kb_result:
            context = (
                f"Relevant Knowledge Base Article:\n"
                f"Title: {kb_result.get('title')}\n"
                f"Steps:\n{chr(10).join(kb_result.get('steps', []))}\n"
            )
            if kb_result.get("follow_up"):
                context += f"Follow-up: {kb_result.get('follow_up')}\n"
            
            messages.append(SystemMessage(content=f"Context:\n{context}"))
            
        # Add conversation history (last 5 turns to keep context manageable)
        for entry in history[-5:]:
            role = entry.get("role")
            content = entry.get("content")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(SystemMessage(content=f"Assistant: {content}"))
                
        # Add current message
        messages.append(HumanMessage(content=message))
        
        # Invoke LLM
        response = await self.llm.ainvoke(messages)
        return response.content
