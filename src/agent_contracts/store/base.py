"""StateStore - Abstract base class for state storage.

Provides an interface for persistent state storage.
Implement this for your storage backend (Redis, PostgreSQL, etc.).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StateStore(ABC):
    """Abstract base class for state storage.
    
    Implement this for your storage backend.
    
    Example:
        class RedisStateStore(StateStore):
            async def save(self, key: str, value: dict) -> None:
                await self.redis.set(key, json.dumps(value))
            
            async def load(self, key: str) -> dict | None:
                data = await self.redis.get(key)
                return json.loads(data) if data else None
    """

    @abstractmethod
    async def save(self, key: str, value: dict[str, Any]) -> None:
        """Save value for key.
        
        Args:
            key: Storage key
            value: Value to store
        """
        ...

    @abstractmethod
    async def load(self, key: str) -> dict[str, Any] | None:
        """Load value for key.
        
        Args:
            key: Storage key
            
        Returns:
            Stored value or None if not found
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value for key.
        
        Args:
            key: Storage key
            
        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists.
        
        Args:
            key: Storage key
            
        Returns:
            True if exists
        """
        ...

    async def list_by_prefix(self, prefix: str) -> list[str]:
        """List keys matching prefix.
        
        Optional method - override if your backend supports it.
        
        Args:
            prefix: Key prefix
            
        Returns:
            List of matching keys
        """
        return []

    async def close(self) -> None:
        """Cleanup resources.
        
        Optional method - override if your backend needs cleanup.
        """
        pass
