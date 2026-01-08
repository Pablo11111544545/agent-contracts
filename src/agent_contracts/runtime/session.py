"""Session storage abstraction."""
from __future__ import annotations

from typing import Protocol, runtime_checkable, Any
import time


@runtime_checkable
class SessionStore(Protocol):
    """Protocol for session persistence.
    
    Implement this protocol to provide session storage
    (e.g., PostgreSQL, Redis, DynamoDB).
    
    Example:
        >>> class RedisSessionStore:
        ...     def __init__(self, redis_client):
        ...         self.redis = redis_client
        ...     
        ...     async def load(self, session_id: str) -> dict | None:
        ...         data = await self.redis.get(f"session:{session_id}")
        ...         return json.loads(data) if data else None
        ...     
        ...     async def save(self, session_id: str, data: dict, ttl: int = 3600):
        ...         await self.redis.setex(
        ...             f"session:{session_id}",
        ...             ttl,
        ...             json.dumps(data),
        ...         )
    """
    
    async def load(self, session_id: str) -> dict[str, Any] | None:
        """Load session data.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Session data dict, or None if not found
        """
        ...
    
    async def save(
        self, 
        session_id: str, 
        data: dict[str, Any], 
        ttl_seconds: int = 3600,
    ) -> None:
        """Save session data.
        
        Args:
            session_id: The session identifier
            data: Session data to persist
            ttl_seconds: Time-to-live in seconds (default 1 hour)
        """
        ...
    
    async def delete(self, session_id: str) -> None:
        """Delete session data.
        
        Args:
            session_id: The session identifier
        """
        ...


class InMemorySessionStore:
    """In-memory session store for development/testing.
    
    NOT suitable for production use - data is lost on restart.
    
    Example:
        >>> store = InMemorySessionStore()
        >>> await store.save("session1", {"user": "test"})
        >>> data = await store.load("session1")
        >>> print(data)  # {"user": "test"}
    """
    
    def __init__(self) -> None:
        """Initialize the store."""
        self._store: dict[str, tuple[dict[str, Any], float]] = {}
    
    async def load(self, session_id: str) -> dict[str, Any] | None:
        """Load session data.
        
        Returns None if session doesn't exist or has expired.
        """
        entry = self._store.get(session_id)
        if entry is None:
            return None
        
        data, expires_at = entry
        if time.time() > expires_at:
            # Expired - clean up and return None
            del self._store[session_id]
            return None
        
        return data
    
    async def save(
        self, 
        session_id: str, 
        data: dict[str, Any], 
        ttl_seconds: int = 3600,
    ) -> None:
        """Save session data with TTL."""
        expires_at = time.time() + ttl_seconds
        self._store[session_id] = (data, expires_at)
    
    async def delete(self, session_id: str) -> None:
        """Delete session data."""
        self._store.pop(session_id, None)
    
    def clear(self) -> None:
        """Clear all sessions (useful for testing)."""
        self._store.clear()
    
    def __len__(self) -> int:
        """Return number of stored sessions."""
        return len(self._store)
