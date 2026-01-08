"""BaseActionRouter - Action-based routing.

Parses action parameters and routes to appropriate subgraphs.
Uses rule-based decisions, no LLM.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from agent_contracts.utils.logging import get_logger

logger = get_logger("agent_contracts.router")


class BaseActionRouter(ABC):
    """Base class for action-based routing.
    
    All requests are routed here first based on action.
    Uses only parameters, no LLM.
    
    Example:
        class MyRouter(BaseActionRouter):
            def route(self, action: str, state: dict | None = None) -> str:
                if action == "create":
                    return "create_supervisor"
                elif action == "search":
                    return "search_supervisor"
                return "default_supervisor"
    """
    
    @abstractmethod
    def route(self, action: str, state: dict | None = None) -> str:
        """Determine routing target based on action.
        
        Args:
            action: Request action
            state: Agent state (optional)
            
        Returns:
            Routing target node name
            
        Raises:
            ValueError: For unknown actions
        """
        ...
    
    def __call__(self, state: dict) -> dict:
        """Execute as LangGraph node.
        
        Args:
            state: Agent state
            
        Returns:
            Updated state (includes _internal.next_node)
        """
        request = state.get("request", {})
        action = request.get("action", "")
        
        try:
            next_node = self.route(action, state)
            logger.info(f"Routed: action={action} -> {next_node}")
            # LangGraph reducer merges this into existing _internal slice
            return {"_internal": {"next_node": next_node}}
        except ValueError as e:
            logger.error(f"Routing failed: {e}")
            # LangGraph reducer merges these updates into existing slices
            return {
                "_internal": {"next_node": None, "error": str(e)},
                "response": {
                    "response_type": "error",
                    "response_data": {"code": "UNKNOWN_ACTION", "message": str(e)},
                },
            }
