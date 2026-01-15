"""State Operations - Higher-level state manipulation helpers.

Provides immutable helper functions for common state operations like
merging sessions, resetting flags, and creating initial state.

All functions follow immutable patterns - they return new state dictionaries
rather than mutating the input.
"""
from __future__ import annotations

from typing import Any

from agent_contracts.state_accessors import (
    StateAccessor,
    Internal,
    Request,
    Response,
    reset_response,
)


def ensure_slices(state: dict, slice_names: list[str]) -> dict:
    """Ensure specified slices exist in state (immutable).
    
    Creates empty dicts for any missing slices.
    
    Args:
        state: Current state
        slice_names: List of slice names to ensure exist
        
    Returns:
        New state with all specified slices present
        
    Example:
        >>> state = {}
        >>> state = ensure_slices(state, ["request", "response", "_internal"])
        >>> "request" in state  # True
    """
    result = dict(state)
    for name in slice_names:
        if name not in result or not isinstance(result.get(name), dict):
            result[name] = {}
    return result


def merge_session(
    state: dict, 
    session_data: dict, 
    slices: list[str] | None = None,
) -> dict:
    """Merge session data into state (immutable).
    
    For each specified slice, merges session data with current state.
    Does not create new slices if they don't exist in session_data.
    
    Args:
        state: Current state
        session_data: Session data to merge
        slices: Slice names to merge (default: ["_internal"])
        
    Returns:
        New state with session data merged
        
    Example:
        >>> state = {"workflow": {"count": 1}}
        >>> session = {"workflow": {"history": ["step1"]}}
        >>> merged = merge_session(state, session, ["workflow"])
        >>> merged["workflow"]  # {"count": 1, "history": ["step1"]}
    """
    if slices is None:
        slices = ["_internal"]
    
    result = dict(state)
    for slice_name in slices:
        if slice_name in session_data:
            current_slice = result.get(slice_name, {})
            if not isinstance(current_slice, dict):
                current_slice = {}
            session_slice = session_data[slice_name]
            if isinstance(session_slice, dict):
                result[slice_name] = {**current_slice, **session_slice}
    
    return result


def reset_internal_flags(
    state: dict,
    flags: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict:
    """Reset internal flags to specified values (immutable).
    
    Can pass flags as a dict or as keyword arguments.
    Only resets flags that have corresponding accessors in Internal.
    
    Args:
        state: Current state
        flags: Dict of flag_name -> value to set
        **kwargs: Alternative way to specify flags
        
    Returns:
        New state with flags reset
        
    Example:
        >>> state = reset_internal_flags(state, 
        ...     turn_count=0,
        ...     is_first_turn=True,
        ... )
    """
    all_flags = {**(flags or {}), **kwargs}
    result = state
    
    for flag_name, value in all_flags.items():
        accessor = getattr(Internal, flag_name, None)
        if accessor is not None and isinstance(accessor, StateAccessor):
            result = accessor.set(result, value)
    
    return result


def create_base_state(
    session_id: str = "",
    action: str = "",
    params: dict | None = None,
    message: str | None = None,
    image: str | None = None,
    active_mode: str | None = None,
) -> dict:
    """Create a minimal base state with request and internal slices.
    
    This is a simplified state factory for OSS use. Applications may
    need to extend this with additional slices.
    
    Args:
        session_id: Session identifier
        action: Action to perform
        params: Optional action parameters
        message: Optional user message
        image: Optional base64-encoded image
        active_mode: Optional initial mode
        
    Returns:
        New state dict with request, response, and _internal slices
        
    Example:
        >>> state = create_base_state(
        ...     session_id="abc123",
        ...     action="answer",
        ...     message="I like casual style",
        ... )
    """
    state: dict = {}
    
    # Request slice
    state = Request.session_id.set(state, session_id)
    state = Request.action.set(state, action)
    state = Request.params.set(state, params)
    state = Request.message.set(state, message)
    state = Request.image.set(state, image)
    
    # Response slice (empty)
    state = reset_response(state)
    
    # Internal slice
    state = Internal.turn_count.set(state, 0)
    state = Internal.is_first_turn.set(state, True)
    state = Internal.active_mode.set(state, active_mode)
    state = Internal.next_node.set(state, None)
    state = Internal.decision.set(state, None)
    state = Internal.error.set(state, None)
    
    return state


def copy_slice(state: dict, slice_name: str) -> dict:
    """Get a shallow copy of a slice from state.
    
    Args:
        state: Current state
        slice_name: Name of slice to copy
        
    Returns:
        Copy of the slice dict, or empty dict if not present
    """
    slice_data = state.get(slice_name, {})
    if isinstance(slice_data, dict):
        return dict(slice_data)
    return {}


def update_slice(state: dict, slice_name: str, **updates: Any) -> dict:
    """Update multiple fields in a slice at once (immutable).
    
    Args:
        state: Current state
        slice_name: Name of slice to update
        **updates: Field updates as keyword arguments
        
    Returns:
        New state with slice updated
        
    Example:
        >>> state = update_slice(state, "workflow",
        ...     step_count=5,
        ...     current_step={"name": "..."},
        ... )
    """
    current_slice = state.get(slice_name, {})
    if not isinstance(current_slice, dict):
        current_slice = {}
    new_slice = {**current_slice, **updates}
    return {**state, slice_name: new_slice}


def get_nested(state: dict, *keys: str, default: Any = None) -> Any:
    """Get a nested value from state using a path of keys.
    
    Args:
        state: Current state
        *keys: Path of keys to traverse
        default: Default value if path not found
        
    Returns:
        Value at path, or default
        
    Example:
        >>> state = {"workflow": {"collected_info": {"name": "Alice"}}}
        >>> get_nested(state, "workflow", "collected_info", "name")  # "Alice"
        >>> get_nested(state, "workflow", "missing", default="unknown")  # "unknown"
    """
    current = state
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current
