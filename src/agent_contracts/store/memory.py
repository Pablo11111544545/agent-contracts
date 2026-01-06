"""InMemoryStateStore - In-memory state storage.

Simple in-process storage for development and testing.
Not suitable for production use with multiple processes.
"""
from __future__ import annotations

from typing import Any

from agent_contracts.store.base import StateStore


class InMemoryStateStore(StateStore):
    """In-memory state storage.
    
    Simple in-process dictionary storage.
    Useful for development and testing.
    
    Example:
        store = InMemoryStateStore()
        await store.save("user:123", {"name": "John"})
        data = await store.load("user:123")
    """

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}

    async def save(self, key: str, value: dict[str, Any]) -> None:
        self._data[key] = value

    async def load(self, key: str) -> dict[str, Any] | None:
        return self._data.get(key)

    async def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        return key in self._data

    async def list_by_prefix(self, prefix: str) -> list[str]:
        return [k for k in self._data.keys() if k.startswith(prefix)]
    
    def clear(self) -> None:
        """Clear all stored data (for testing)."""
        self._data.clear()
