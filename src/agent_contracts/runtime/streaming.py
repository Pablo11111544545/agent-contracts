"""Streaming execution support for agent runtime.

Provides streaming capabilities for node-by-node execution,
enabling SSE (Server-Sent Events) and progressive response patterns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Literal
from enum import Enum
import logging

from agent_contracts.runtime.context import RequestContext, ExecutionResult
from agent_contracts.runtime.hooks import RuntimeHooks, DefaultHooks
from agent_contracts.runtime.session import SessionStore
from agent_contracts.runtime.state_ops import create_base_state, merge_session
from agent_contracts.state_accessors import Internal
from agent_contracts.state import apply_slice_updates

logger = logging.getLogger(__name__)


class StreamEventType(str, Enum):
    """Types of streaming events."""
    NODE_START = "node_start"      # Node execution starting
    NODE_END = "node_end"          # Node execution completed
    STATUS = "status"              # Status update message
    PROGRESS = "progress"          # Progress indicator
    DATA = "data"                  # Intermediate data
    ERROR = "error"                # Error occurred
    DONE = "done"                  # Execution complete


@dataclass
class StreamEvent:
    """Event emitted during streaming execution.
    
    Attributes:
        type: Type of event (node_start, node_end, status, etc.)
        node_name: Name of node (for node events)
        data: Event data payload
        message: Human-readable message
        state: State snapshot (optional)
    
    Example:
        >>> event = StreamEvent(
        ...     type=StreamEventType.NODE_END,
        ...     node_name="search",
        ...     data={"results_count": 10},
        ... )
    """
    type: StreamEventType | str
    node_name: str | None = None
    data: dict[str, Any] | None = None
    message: str | None = None
    state: dict[str, Any] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "type": self.type.value if isinstance(self.type, StreamEventType) else self.type,
        }
        if self.node_name:
            result["node_name"] = self.node_name
        if self.data:
            result["data"] = self.data
        if self.message:
            result["message"] = self.message
        return result
    
    def to_sse(self) -> str:
        """Format as Server-Sent Event string."""
        import json
        event_type = self.type.value if isinstance(self.type, StreamEventType) else self.type
        data = json.dumps(self.to_dict(), ensure_ascii=False)
        return f"event: {event_type}\ndata: {data}\n\n"


@dataclass
class NodeExecutor:
    """Wrapper for executing a single node.
    
    Attributes:
        name: Node name
        func: Async function that takes state and returns updates
        description: Optional description for status messages
    """
    name: str
    func: Callable[[dict], Any]  # async (state) -> updates
    description: str | None = None


class StreamingRuntime:
    """Runtime with streaming execution support.
    
    Enables node-by-node execution with events emitted for each step,
    suitable for SSE streaming to clients.
    
    Example:
        >>> runtime = StreamingRuntime(nodes=[
        ...     NodeExecutor("search", search_node),
        ...     NodeExecutor("stylist", stylist_node),
        ... ])
        >>> 
        >>> async for event in runtime.stream(request):
        ...     yield event.to_sse()
    """
    
    def __init__(
        self,
        nodes: list[NodeExecutor] | None = None,
        hooks: RuntimeHooks | None = None,
        session_store: SessionStore | None = None,
        slices_to_restore: list[str] | None = None,
    ) -> None:
        """Initialize the streaming runtime.
        
        Args:
            nodes: List of node executors to run in sequence
            hooks: Custom runtime hooks
            session_store: Session persistence store
            slices_to_restore: Slice names to restore from session
        """
        self.nodes = nodes or []
        self.hooks = hooks or DefaultHooks()
        self.session_store = session_store
        self.slices_to_restore = slices_to_restore or ["_internal"]
    
    def add_node(self, name: str, func: Callable, description: str | None = None) -> "StreamingRuntime":
        """Add a node to the execution pipeline (fluent API).
        
        Args:
            name: Node name
            func: Async function that takes state and returns updates
            description: Optional description
            
        Returns:
            self for chaining
        """
        self.nodes.append(NodeExecutor(name=name, func=func, description=description))
        return self
    
    async def stream(
        self,
        request: RequestContext,
        initial_state: dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Execute nodes and yield streaming events.
        
        Args:
            request: Execution request context
            initial_state: Optional pre-built initial state
            
        Yields:
            StreamEvent for each execution step
        """
        try:
            # 1. Build initial state
            if initial_state is not None:
                state = initial_state
            else:
                state = create_base_state(
                    session_id=request.session_id,
                    action=request.action,
                    params=request.params,
                    message=request.message,
                    image=request.image,
                )
            
            # 2. Restore session if resuming
            if request.resume_session and self.session_store:
                session_data = await self.session_store.load(request.session_id)
                if session_data:
                    state = merge_session(state, session_data, self.slices_to_restore)
                    logger.debug(f"Restored session {request.session_id}")
            
            # 3. Apply prepare_state hook
            state = await self.hooks.prepare_state(state, request)
            
            # 4. Execute nodes in sequence
            for node_executor in self.nodes:
                # Emit node start
                yield StreamEvent(
                    type=StreamEventType.NODE_START,
                    node_name=node_executor.name,
                    message=node_executor.description or f"Executing {node_executor.name}...",
                )
                
                try:
                    # Execute node
                    updates = await node_executor.func(state)
                    
                    # Apply updates
                    if updates:
                        state = apply_slice_updates(state, updates)
                    
                    # Emit node end
                    yield StreamEvent(
                        type=StreamEventType.NODE_END,
                        node_name=node_executor.name,
                        data=updates,
                        state=state,
                    )
                    
                except Exception as e:
                    logger.error(f"Node {node_executor.name} failed: {e}", exc_info=True)
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        node_name=node_executor.name,
                        message=str(e),
                    )
                    return
            
            # 5. Build final result
            result = ExecutionResult.from_state(state)
            
            # 6. Apply after_execution hook
            await self.hooks.after_execution(state, result)
            
            # 7. Emit done
            yield StreamEvent(
                type=StreamEventType.DONE,
                data=result.to_response_dict(),
                state=state,
            )
            
        except Exception as e:
            logger.error(f"Streaming execution failed: {e}", exc_info=True)
            yield StreamEvent(
                type=StreamEventType.ERROR,
                message=str(e),
            )
    
    async def stream_with_graph(
        self,
        request: RequestContext,
        graph: Any,
        stream_mode: str = "updates",
    ) -> AsyncIterator[StreamEvent]:
        """Stream execution using LangGraph's native streaming.
        
        Uses LangGraph's astream() method for true streaming support.
        
        Args:
            request: Execution request context
            graph: Compiled LangGraph graph
            stream_mode: LangGraph stream mode ("values", "updates", "debug")
            
        Yields:
            StreamEvent for each update from the graph
        """
        try:
            # Build initial state
            state = create_base_state(
                session_id=request.session_id,
                action=request.action,
                params=request.params,
                message=request.message,
                image=request.image,
            )
            
            # Restore session
            if request.resume_session and self.session_store:
                session_data = await self.session_store.load(request.session_id)
                if session_data:
                    state = merge_session(state, session_data, self.slices_to_restore)
            
            # Apply hooks
            state = await self.hooks.prepare_state(state, request)
            
            # Stream from graph
            final_state = state
            async for chunk in graph.astream(state, stream_mode=stream_mode):
                if stream_mode == "updates":
                    # chunk is dict of {node_name: update}
                    for node_name, update in chunk.items():
                        yield StreamEvent(
                            type=StreamEventType.NODE_END,
                            node_name=node_name,
                            data=update if isinstance(update, dict) else {"value": update},
                        )
                        if isinstance(update, dict):
                            final_state = apply_slice_updates(final_state, update)
                else:
                    # chunk is the state
                    yield StreamEvent(
                        type=StreamEventType.DATA,
                        data=chunk if isinstance(chunk, dict) else {"value": chunk},
                    )
                    if isinstance(chunk, dict):
                        final_state = chunk
            
            # Build result
            result = ExecutionResult.from_state(final_state)
            await self.hooks.after_execution(final_state, result)
            
            yield StreamEvent(
                type=StreamEventType.DONE,
                data=result.to_response_dict(),
            )
            
        except Exception as e:
            logger.error(f"Graph streaming failed: {e}", exc_info=True)
            yield StreamEvent(
                type=StreamEventType.ERROR,
                message=str(e),
            )


def create_status_event(message: str) -> StreamEvent:
    """Helper to create a status event."""
    return StreamEvent(type=StreamEventType.STATUS, message=message)


def create_progress_event(current: int, total: int, message: str | None = None) -> StreamEvent:
    """Helper to create a progress event."""
    return StreamEvent(
        type=StreamEventType.PROGRESS,
        data={"current": current, "total": total},
        message=message,
    )


def create_data_event(data: dict[str, Any], message: str | None = None) -> StreamEvent:
    """Helper to create a data event."""
    return StreamEvent(type=StreamEventType.DATA, data=data, message=message)
