"""Request/Response context types for runtime execution."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RequestContext:
    """Context for an agent execution request.
    
    Contains all information needed to build initial state and execute the graph.
    
    Attributes:
        session_id: Unique session identifier
        action: The action to perform (e.g., "answer", "propose")
        params: Optional parameters for the action
        message: Optional user message
        image: Optional base64-encoded image
        resume_session: Whether to restore previous session state
        metadata: Additional app-specific metadata
    
    Example:
        >>> ctx = RequestContext(
        ...     session_id="abc123",
        ...     action="answer",
        ...     message="I prefer casual style",
        ...     resume_session=True,
        ... )
    """
    session_id: str
    action: str
    params: dict[str, Any] | None = None
    message: str | None = None
    image: str | None = None
    resume_session: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """Get a parameter value safely.
        
        Args:
            key: Parameter key
            default: Default value if not found
            
        Returns:
            Parameter value or default
        """
        if self.params is None:
            return default
        return self.params.get(key, default)


@dataclass
class ExecutionResult:
    """Result of an agent execution.
    
    Contains the final state and response information.
    
    Attributes:
        state: The final state after graph execution
        response_type: Type of response (e.g., "question", "result")
        response_data: Response payload data
        response_message: Optional response message
        success: Whether execution completed successfully
        error: Error message if execution failed
    
    Example:
        >>> result = ExecutionResult(
        ...     state=final_state,
        ...     response_type="question",
        ...     response_data={"question": "What's your preference?"},
        ... )
    """
    state: dict[str, Any]
    response_type: str | None = None
    response_data: dict[str, Any] | None = None
    response_message: str | None = None
    success: bool = True
    error: str | None = None
    
    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "ExecutionResult":
        """Create ExecutionResult from final state.
        
        Extracts response information from the response slice.
        
        Args:
            state: Final state after graph execution
            
        Returns:
            ExecutionResult instance
        """
        response = state.get("response", {}) or {}
        return cls(
            state=state,
            response_type=response.get("response_type"),
            response_data=response.get("response_data"),
            response_message=response.get("response_message"),
        )
    
    @classmethod
    def error_result(cls, error: str, state: dict[str, Any] | None = None) -> "ExecutionResult":
        """Create an error ExecutionResult.
        
        Args:
            error: Error message
            state: Optional partial state
            
        Returns:
            ExecutionResult with success=False
        """
        return cls(
            state=state or {},
            success=False,
            error=error,
        )
    
    def to_response_dict(self) -> dict[str, Any]:
        """Convert to API response dictionary.
        
        Note: response_type takes precedence over any 'type' key in response_data.
        
        Returns:
            Dict suitable for API response
        """
        if not self.success:
            return {
                "type": "error",
                "error": self.error,
            }
        # Expand response_data first, then override with response_type to prevent
        # accidental overwriting if response_data contains a 'type' key
        result = dict(self.response_data or {})
        result["type"] = self.response_type or "unknown"
        return result
