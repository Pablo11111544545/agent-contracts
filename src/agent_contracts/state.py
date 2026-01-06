"""State Slices - Domain-separated State.

Following LangGraph best practices, State is separated by domain.
Each node declares and accesses only the slices it needs via Contract.
"""
from __future__ import annotations

from typing import Any, TypedDict


# =============================================================================
# Base Slices (Generic - Extend in your project)
# =============================================================================

class BaseRequestSlice(TypedDict, total=False):
    """Base request information (read-only).
    
    Set from API request, nodes typically only read.
    """
    session_id: str
    action: str
    params: dict | None
    message: str | None
    image: str | None


class BaseResponseSlice(TypedDict, total=False):
    """Base response information.
    
    Holds information to return as API response.
    """
    response_type: str | None
    response_data: dict | None
    response_message: str | None


class BaseInternalSlice(TypedDict, total=False):
    """Internal flags (for Supervisor/Router).
    
    Nodes should not access these directly.
    """
    active_mode: str | None
    turn_count: int
    is_first_turn: bool
    next_node: str | None
    decision: str | None
    error: str | None


# =============================================================================
# Base Agent State
# =============================================================================

class BaseAgentState(TypedDict, total=False):
    """Base Agent State - Extend in your project.
    
    This provides the minimal state structure.
    Add your domain slices by subclassing.
    
    Example:
        class MyAgentState(BaseAgentState):
            user: UserSlice
            shopping: ShoppingSlice
    """
    request: BaseRequestSlice
    response: BaseResponseSlice
    _internal: BaseInternalSlice


# =============================================================================
# Helper Functions
# =============================================================================

def get_slice(state: dict, slice_name: str) -> dict:
    """Get specified slice from state.
    
    Args:
        state: AgentState or dict
        slice_name: Slice name (request, response, _internal, etc.)
        
    Returns:
        Slice dict (empty dict if not found)
    """
    return state.get(slice_name, {})


def merge_slice_updates(state: dict, updates: dict[str, Any] | None) -> dict[str, Any]:
    """Merge slice-level updates for LangGraph.
    
    Args:
        state: Current state
        updates: {slice_name: {field: value, ...}, ...}
        
    Returns:
        Merged update dict (full slices)
    """
    if not updates:
        return {}

    merged: dict[str, Any] = {}
    for slice_name, slice_updates in updates.items():
        current_slice = state.get(slice_name, {})
        if isinstance(current_slice, dict) and isinstance(slice_updates, dict):
            merged[slice_name] = {**current_slice, **slice_updates}
        else:
            merged[slice_name] = slice_updates
    return merged


def apply_slice_updates(state: dict, updates: dict[str, Any] | None) -> dict:
    """Apply updates to state and return new state."""
    merged_updates = merge_slice_updates(state, updates)
    if not merged_updates:
        return dict(state)
    new_state = dict(state)
    new_state.update(merged_updates)
    return new_state
