"""State Summarizer - Recursive state slice summarization for LLM context.

Provides intelligent summarization of state slices with:
- Recursive traversal of nested structures
- Depth limiting to prevent excessive nesting
- Item count limiting for large collections
- Structure preservation for better readability
"""
from __future__ import annotations

from typing import Any


class StateSummarizer:
    """Recursively summarize state slices for LLM context.
    
    Preserves hierarchical structure while limiting size at each level.
    Useful for providing rich context to LLMs without overwhelming token budgets.
    
    Example:
        summarizer = StateSummarizer(max_depth=2, max_dict_items=3)
        summary = summarizer.summarize(large_state_slice)
        # Returns: "{'key1': 'value1', 'key2': [...], ...} (10 items total)"
    """
    
    def __init__(
        self,
        max_depth: int = 5,
        max_dict_items: int = 5,
        max_list_items: int = 5,
        max_str_length: int = 400,
    ):
        """Initialize summarizer.
        
        Args:
            max_depth: Maximum recursion depth (0 = no recursion)
            max_dict_items: Maximum dictionary items to show per level
            max_list_items: Maximum list items to show per level
            max_str_length: Maximum string length before truncation
        """
        self.max_depth = max_depth
        self.max_dict_items = max_dict_items
        self.max_list_items = max_list_items
        self.max_str_length = max_str_length
    
    def summarize(self, value: Any) -> str:
        """Summarize a value recursively.
        
        Args:
            value: Value to summarize (dict, list, str, etc.)
            
        Returns:
            Human-readable summary string
        """
        return self._summarize_value(value, depth=0, seen=set())
    
    def _summarize_value(self, value: Any, depth: int, seen: set[int]) -> str:
        """Recursively summarize a value.
        
        Args:
            value: Value to summarize
            depth: Current recursion depth
            seen: Set of object IDs already visited (for cycle detection)
            
        Returns:
            Summary string
        """
        # Cycle detection for mutable containers
        if isinstance(value, (dict, list, tuple)):
            obj_id = id(value)
            if obj_id in seen:
                return "<cycle>"
            # Create new set with current object ID
            seen = seen | {obj_id}
        
        if value is None:
            return "None"
        
        if isinstance(value, bool):
            return str(value)
        
        if isinstance(value, (int, float)):
            return str(value)
        
        if isinstance(value, str):
            return self._summarize_string(value)
        
        if isinstance(value, dict):
            return self._summarize_dict(value, depth, seen)
        
        if isinstance(value, (list, tuple)):
            return self._summarize_list(value, depth, seen)
        
        # For other types (objects, etc.), use repr with length limit
        repr_str = repr(value)
        if len(repr_str) > self.max_str_length:
            return f"{repr_str[:self.max_str_length]}..."
        return repr_str
    
    def _summarize_string(self, value: str) -> str:
        """Summarize a string value.
        
        Args:
            value: String to summarize
            
        Returns:
            Truncated string with ellipsis if needed
        """
        if len(value) <= self.max_str_length:
            return repr(value)
        return f"{repr(value[:self.max_str_length])}..."
    
    def _summarize_dict(self, value: dict, depth: int, seen: set[int]) -> str:
        """Summarize a dictionary recursively.
        
        Args:
            value: Dictionary to summarize
            depth: Current recursion depth
            seen: Set of visited object IDs for cycle detection
            
        Returns:
            Summary string like "{'key1': 'val1', 'key2': {...}, ...} (10 items)"
        """
        if not value:
            return "{}"
        
        total_items = len(value)
        
        # If at max depth, just show keys
        if depth >= self.max_depth:
            keys = list(value.keys())[:self.max_dict_items]
            keys_str = ", ".join(repr(k) for k in keys)
            if total_items > self.max_dict_items:
                return f"{{{keys_str}, ...}} ({total_items} items)"
            return f"{{{keys_str}}} ({total_items} items)"
        
        # Recursively summarize items
        items = []
        for i, (k, v) in enumerate(value.items()):
            if i >= self.max_dict_items:
                break
            key_str = repr(k)
            val_str = self._summarize_value(v, depth + 1, seen)
            items.append(f"{key_str}: {val_str}")
        
        items_str = ", ".join(items)
        
        if total_items > self.max_dict_items:
            return f"{{{items_str}, ...}} ({total_items} items)"
        return f"{{{items_str}}}"
    
    def _summarize_list(self, value: list | tuple, depth: int, seen: set[int]) -> str:
        """Summarize a list or tuple recursively.
        
        Args:
            value: List or tuple to summarize
            depth: Current recursion depth
            seen: Set of visited object IDs for cycle detection
            
        Returns:
            Summary string like "[item1, item2, ...] (10 items)"
        """
        if not value:
            return "[]" if isinstance(value, list) else "()"
        
        total_items = len(value)
        bracket_open = "[" if isinstance(value, list) else "("
        bracket_close = "]" if isinstance(value, list) else ")"
        
        # If at max depth, just show count
        if depth >= self.max_depth:
            if total_items > self.max_list_items:
                return f"{bracket_open}...{bracket_close} ({total_items} items)"
            # Show first few items without recursion
            items_str = ", ".join(repr(v) for v in list(value)[:self.max_list_items])
            return f"{bracket_open}{items_str}{bracket_close}"
        
        # Recursively summarize items
        items = []
        for i, item in enumerate(value):
            if i >= self.max_list_items:
                break
            items.append(self._summarize_value(item, depth + 1, seen))
        
        items_str = ", ".join(items)
        
        if total_items > self.max_list_items:
            return f"{bracket_open}{items_str}, ...{bracket_close} ({total_items} items)"
        return f"{bracket_open}{items_str}{bracket_close}"


def summarize_state_slice(
    value: Any,
    max_depth: int = 2,
    max_dict_items: int = 3,
    max_list_items: int = 2,
    max_str_length: int = 50,
) -> str:
    """Convenience function to summarize a state slice.
    
    Args:
        value: Value to summarize
        max_depth: Maximum recursion depth
        max_dict_items: Maximum dictionary items per level
        max_list_items: Maximum list items per level
        max_str_length: Maximum string length
        
    Returns:
        Summary string
        
    Example:
        summary = summarize_state_slice(state["profile"], max_depth=2)
    """
    summarizer = StateSummarizer(
        max_depth=max_depth,
        max_dict_items=max_dict_items,
        max_list_items=max_list_items,
        max_str_length=max_str_length,
    )
    return summarizer.summarize(value)

# Made with Bob
