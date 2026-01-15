"""Runtime hooks for customization."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from agent_contracts.runtime.context import RequestContext, ExecutionResult


@runtime_checkable
class RuntimeHooks(Protocol):
    """Protocol for runtime customization hooks.
    
    Implement this protocol to customize the execution lifecycle.
    Hooks are called at specific points during execution:
    
    1. prepare_state: Called before graph execution to customize initial state
    2. after_execution: Called after graph execution for cleanup/persistence
    
    Example:
        >>> class MyHooks:
        ...     async def prepare_state(self, state, request):
        ...         # Add custom data to state
        ...         state = Internal.active_mode.set(state, "orders")
        ...         return state
        ...     
        ...     async def after_execution(self, state, result):
        ...         # Persist session if needed
        ...         await self.session_store.save(...)
    """
    
    async def prepare_state(
        self, 
        state: dict, 
        request: RequestContext,
    ) -> dict:
        """Prepare state before graph execution.
        
        Called after initial state creation and session restoration.
        Use this to add app-specific state modifications.
        
        Args:
            state: Initial state (may include restored session data)
            request: The execution request context
            
        Returns:
            Modified state (should be immutable - return new dict)
        """
        ...
    
    async def after_execution(
        self, 
        state: dict, 
        result: ExecutionResult,
    ) -> None:
        """Handle post-execution tasks.
        
        Called after graph execution completes.
        Use this for session persistence, cleanup, logging, etc.
        
        Args:
            state: Final state after graph execution
            result: The execution result
        """
        ...


class DefaultHooks:
    """Default implementation of RuntimeHooks (no-op).
    
    Use this when no customization is needed, or as a base class
    for partial implementations.
    """
    
    async def prepare_state(
        self, 
        state: dict, 
        request: RequestContext,
    ) -> dict:
        """Default: return state unchanged."""
        return state
    
    async def after_execution(
        self, 
        state: dict, 
        result: ExecutionResult,
    ) -> None:
        """Default: do nothing."""
        pass
