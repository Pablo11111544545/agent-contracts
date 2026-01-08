"""State Accessors - Type-safe state access pattern.

Provides immutable, type-safe access to state fields following
the Redux selector pattern. All state modifications return new
state dictionaries rather than mutating in place.

Example:
    >>> state = {"_internal": {"turn_count": 5}}
    >>> count = Internal.turn_count.get(state)  # 5
    >>> new_state = Internal.turn_count.set(state, 10)
    >>> Internal.turn_count.get(new_state)  # 10
    >>> Internal.turn_count.get(state)  # 5 (original unchanged)
"""
from __future__ import annotations

from typing import TypeVar, Generic, overload

T = TypeVar("T")


class StateAccessor(Generic[T]):
    """Type-safe accessor for state fields.
    
    Provides get/set methods that work immutably on state dictionaries.
    The accessor knows its slice name, field name, and default value.
    
    Attributes:
        slice_name: Name of the state slice (e.g., "_internal", "request")
        field_name: Name of the field within the slice
        default: Default value if field is not present
    
    Example:
        >>> turn_count = StateAccessor("_internal", "turn_count", 0)
        >>> state = {}
        >>> turn_count.get(state)  # Returns 0 (default)
        >>> new_state = turn_count.set(state, 5)
        >>> turn_count.get(new_state)  # Returns 5
    """
    
    __slots__ = ("slice_name", "field_name", "default")
    
    def __init__(self, slice_name: str, field_name: str, default: T) -> None:
        """Initialize the accessor.
        
        Args:
            slice_name: Name of the state slice
            field_name: Name of the field within the slice
            default: Default value to return if field is absent
        """
        self.slice_name = slice_name
        self.field_name = field_name
        self.default = default
    
    def get(self, state: dict) -> T:
        """Get the field value from state.
        
        Args:
            state: The state dictionary
            
        Returns:
            The field value, or default if not present
        """
        slice_data = state.get(self.slice_name)
        if not isinstance(slice_data, dict):
            return self.default
        return slice_data.get(self.field_name, self.default)
    
    def set(self, state: dict, value: T) -> dict:
        """Set the field value and return a new state (immutable).
        
        Args:
            state: The current state dictionary
            value: The new value to set
            
        Returns:
            A new state dictionary with the updated value
        """
        current_slice = state.get(self.slice_name, {})
        if not isinstance(current_slice, dict):
            current_slice = {}
        new_slice = {**current_slice, self.field_name: value}
        return {**state, self.slice_name: new_slice}
    
    def update(self, state: dict, func) -> dict:
        """Update the field using a function (immutable).
        
        Args:
            state: The current state dictionary
            func: A function that takes the current value and returns new value
            
        Returns:
            A new state dictionary with the updated value
        """
        current_value = self.get(state)
        new_value = func(current_value)
        return self.set(state, new_value)
    
    def __repr__(self) -> str:
        return f"StateAccessor({self.slice_name!r}, {self.field_name!r}, default={self.default!r})"


# =============================================================================
# Standard Accessors: _internal slice
# =============================================================================

class Internal:
    """Accessors for _internal slice fields.
    
    These fields are used by the supervisor/router and should not be
    accessed directly by nodes.
    """
    
    # Core control fields
    turn_count: StateAccessor[int] = StateAccessor("_internal", "turn_count", 0)
    is_first_turn: StateAccessor[bool] = StateAccessor("_internal", "is_first_turn", True)
    active_mode: StateAccessor[str | None] = StateAccessor("_internal", "active_mode", None)
    next_node: StateAccessor[str | None] = StateAccessor("_internal", "next_node", None)
    decision: StateAccessor[str | None] = StateAccessor("_internal", "decision", None)
    error: StateAccessor[str | None] = StateAccessor("_internal", "error", None)


# =============================================================================
# Standard Accessors: request slice
# =============================================================================

class Request:
    """Accessors for request slice fields.
    
    Request slice contains information from the API request.
    Typically read-only for nodes.
    """
    
    session_id: StateAccessor[str] = StateAccessor("request", "session_id", "")
    action: StateAccessor[str] = StateAccessor("request", "action", "")
    params: StateAccessor[dict | None] = StateAccessor("request", "params", None)
    message: StateAccessor[str | None] = StateAccessor("request", "message", None)
    image: StateAccessor[str | None] = StateAccessor("request", "image", None)


# =============================================================================
# Standard Accessors: response slice
# =============================================================================

class Response:
    """Accessors for response slice fields.
    
    Response slice contains information to return as API response.
    """
    
    response_type: StateAccessor[str | None] = StateAccessor("response", "response_type", None)
    response_data: StateAccessor[dict | None] = StateAccessor("response", "response_data", None)
    response_message: StateAccessor[str | None] = StateAccessor("response", "response_message", None)


# =============================================================================
# Convenience Functions
# =============================================================================

def reset_response(state: dict) -> dict:
    """Reset the response slice to empty values (immutable).
    
    Args:
        state: Current state
        
    Returns:
        New state with response slice cleared
    """
    state = Response.response_type.set(state, None)
    state = Response.response_data.set(state, None)
    state = Response.response_message.set(state, None)
    return state


def increment_turn(state: dict) -> dict:
    """Increment turn count and set is_first_turn to False (immutable).
    
    Args:
        state: Current state
        
    Returns:
        New state with incremented turn count
    """
    state = Internal.turn_count.update(state, lambda x: x + 1)
    state = Internal.is_first_turn.set(state, False)
    return state


def set_error(state: dict, error: str) -> dict:
    """Set error in state (immutable).
    
    Args:
        state: Current state
        error: Error message
        
    Returns:
        New state with error set
    """
    return Internal.error.set(state, error)


def clear_error(state: dict) -> dict:
    """Clear error in state (immutable).
    
    Args:
        state: Current state
        
    Returns:
        New state with error cleared
    """
    return Internal.error.set(state, None)
