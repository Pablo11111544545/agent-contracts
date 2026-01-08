"""Tests for store module - InMemoryStateStore."""

import pytest

from agent_contracts.store import InMemoryStateStore
from agent_contracts.store.base import StateStore


class TestInMemoryStateStore:
    """Tests for InMemoryStateStore."""

    @pytest.fixture
    def store(self):
        """Create a fresh store for each test."""
        return InMemoryStateStore()

    @pytest.mark.asyncio
    async def test_save_and_load(self, store):
        """Test basic save and load operations."""
        await store.save("key1", {"name": "Alice", "age": 30})
        
        result = await store.load("key1")
        
        assert result == {"name": "Alice", "age": 30}

    @pytest.mark.asyncio
    async def test_load_nonexistent_key(self, store):
        """Test loading a key that doesn't exist returns None."""
        result = await store.load("nonexistent")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, store):
        """Test deleting an existing key returns True."""
        await store.save("key1", {"data": "value"})
        
        result = await store.delete("key1")
        
        assert result is True
        assert await store.load("key1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, store):
        """Test deleting a nonexistent key returns False."""
        result = await store.delete("nonexistent")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, store):
        """Test exists returns True for existing key."""
        await store.save("key1", {"data": "value"})
        
        result = await store.exists("key1")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, store):
        """Test exists returns False for nonexistent key."""
        result = await store.exists("nonexistent")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_list_by_prefix(self, store):
        """Test listing keys by prefix."""
        await store.save("user:1", {"name": "Alice"})
        await store.save("user:2", {"name": "Bob"})
        await store.save("session:1", {"data": "x"})
        
        user_keys = await store.list_by_prefix("user:")
        session_keys = await store.list_by_prefix("session:")
        empty_keys = await store.list_by_prefix("unknown:")
        
        assert sorted(user_keys) == ["user:1", "user:2"]
        assert session_keys == ["session:1"]
        assert empty_keys == []

    def test_clear(self, store):
        """Test clearing all data."""
        # Use sync to add data directly
        store._data["key1"] = {"data": "1"}
        store._data["key2"] = {"data": "2"}
        
        store.clear()
        
        assert len(store._data) == 0

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self, store):
        """Test that saving to existing key overwrites."""
        await store.save("key1", {"version": 1})
        await store.save("key1", {"version": 2})
        
        result = await store.load("key1")
        
        assert result == {"version": 2}


class TestStateStoreBase:
    """Tests for StateStore base class."""

    @pytest.mark.asyncio
    async def test_list_by_prefix_default_returns_empty(self):
        """Test that default list_by_prefix returns empty list."""
        # Create a minimal implementation
        class MinimalStore(StateStore):
            async def save(self, key, value):
                pass
            async def load(self, key):
                return None
            async def delete(self, key):
                return False
            async def exists(self, key):
                return False
        
        store = MinimalStore()
        result = await store.list_by_prefix("any:")
        
        assert result == []

    @pytest.mark.asyncio
    async def test_close_default_does_nothing(self):
        """Test that default close() does nothing."""
        class MinimalStore(StateStore):
            async def save(self, key, value):
                pass
            async def load(self, key):
                return None
            async def delete(self, key):
                return False
            async def exists(self, key):
                return False
        
        store = MinimalStore()
        # Should not raise
        await store.close()
