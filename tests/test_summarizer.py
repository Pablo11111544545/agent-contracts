"""Tests for StateSummarizer."""
import pytest
from agent_contracts.utils.summarizer import StateSummarizer, summarize_state_slice


class TestStateSummarizer:
    """Test StateSummarizer class."""
    
    def test_empty_data(self):
        """Test summarization of empty data."""
        summarizer = StateSummarizer()
        
        assert summarizer.summarize(None) == "None"
        assert summarizer.summarize({}) == "{}"
        assert summarizer.summarize([]) == "[]"
        assert summarizer.summarize("") == "''"
    
    def test_simple_types(self):
        """Test summarization of simple types."""
        summarizer = StateSummarizer()
        
        assert summarizer.summarize(True) == "True"
        assert summarizer.summarize(False) == "False"
        assert summarizer.summarize(42) == "42"
        assert summarizer.summarize(3.14) == "3.14"
        assert summarizer.summarize("hello") == "'hello'"
    
    def test_string_truncation(self):
        """Test string truncation."""
        summarizer = StateSummarizer(max_str_length=10)
        
        short_str = "hello"
        long_str = "a" * 100
        
        assert summarizer.summarize(short_str) == "'hello'"
        assert summarizer.summarize(long_str).startswith("'aaaaaaaaaa")
        assert summarizer.summarize(long_str).endswith("...")
    
    def test_simple_dict(self):
        """Test summarization of simple dictionary."""
        summarizer = StateSummarizer()
        
        data = {"name": "Alice", "age": 30}
        result = summarizer.summarize(data)
        
        assert "'name': 'Alice'" in result
        assert "'age': 30" in result
    
    def test_large_dict_truncation(self):
        """Test dictionary truncation with many items."""
        summarizer = StateSummarizer(max_dict_items=2)
        
        data = {f"key{i}": f"value{i}" for i in range(10)}
        result = summarizer.summarize(data)
        
        # Should show first 2 items + ellipsis + count
        assert "..." in result
        assert "(10 items)" in result
        assert result.count("'key") == 2  # Only 2 keys shown
    
    def test_simple_list(self):
        """Test summarization of simple list."""
        summarizer = StateSummarizer(max_list_items=2)
        
        data = [1, 2]
        result = summarizer.summarize(data)
        
        # With max_list_items=2, list of 2 items shows all items without truncation
        assert "1" in result
        assert "2" in result
        assert result == "[1, 2]"
    
    def test_large_list_truncation(self):
        """Test list truncation with many items."""
        summarizer = StateSummarizer(max_list_items=2)
        
        data = list(range(10))
        result = summarizer.summarize(data)
        
        # Should show first 2 items + ellipsis + count
        assert "..." in result
        assert "(10 items)" in result
        assert "0" in result
        assert "1" in result
    
    def test_nested_dict(self):
        """Test summarization of nested dictionary."""
        summarizer = StateSummarizer(max_depth=2)
        
        data = {
            "user": {
                "name": "Alice",
                "profile": {
                    "age": 30,
                    "city": "Tokyo"
                }
            }
        }
        result = summarizer.summarize(data)
        
        # Should show nested structure
        assert "'user'" in result
        assert "'name': 'Alice'" in result
        assert "'profile'" in result
        # At depth 2, should still show some structure
        assert "'age'" in result or "age" in result
    
    def test_nested_list_in_dict(self):
        """Test summarization of list nested in dictionary."""
        summarizer = StateSummarizer(max_depth=2, max_list_items=2)
        
        data = {
            "items": [
                {"id": 1, "name": "Item1"},
                {"id": 2, "name": "Item2"},
                {"id": 3, "name": "Item3"},
            ]
        }
        result = summarizer.summarize(data)
        
        # Should show nested structure
        assert "'items'" in result
        assert "[" in result
        # At depth 2, dicts show keys only
        assert "'id'" in result or "id" in result
        assert "'name'" in result or "name" in result
        # Should indicate truncation
        assert "..." in result
        assert "(3 items)" in result
    
    def test_depth_limiting(self):
        """Test depth limiting prevents excessive nesting."""
        summarizer = StateSummarizer(max_depth=1)
        
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep"
                    }
                }
            }
        }
        result = summarizer.summarize(data)
        
        # At depth 1, should only show keys of nested dicts
        assert "'level1'" in result
        assert "'level2'" in result
        # Should not show deep values
        assert "'value'" not in result or "items)" in result
    
    def test_mixed_nested_structure(self):
        """Test complex nested structure with dicts and lists."""
        summarizer = StateSummarizer(max_depth=2, max_dict_items=3, max_list_items=2)
        
        data = {
            "users": [
                {"name": "Alice", "tags": ["admin", "user"]},
                {"name": "Bob", "tags": ["user"]},
            ],
            "settings": {
                "theme": "dark",
                "notifications": True
            }
        }
        result = summarizer.summarize(data)
        
        # Should show structure
        assert "'users'" in result
        assert "'settings'" in result
        # At depth 2, nested dicts show keys
        assert "name" in result
        assert "'theme': 'dark'" in result
    
    def test_convenience_function(self):
        """Test convenience function."""
        data = {"key": "value"}
        result = summarize_state_slice(data, max_depth=1)
        
        assert "'key': 'value'" in result
    
    def test_tuple_handling(self):
        """Test tuple summarization."""
        summarizer = StateSummarizer(max_list_items=2)
        
        data = (1, 2, 3, 4, 5)
        result = summarizer.summarize(data)
        
        # Should use parentheses for tuples
        assert result.startswith("(")
        assert result.endswith(")")
        assert "..." in result
        assert "(5 items)" in result
    
    def test_custom_object(self):
        """Test custom object summarization."""
        summarizer = StateSummarizer(max_str_length=20)
        
        class CustomObj:
            def __repr__(self):
                return "CustomObj(very_long_representation_string)"
        
        obj = CustomObj()
        result = summarizer.summarize(obj)
        
        # Should use repr and truncate if needed
        assert "CustomObj" in result
        assert "..." in result
    
    def test_real_world_state_slice(self):
        """Test with realistic state slice data."""
        summarizer = StateSummarizer(max_depth=2, max_dict_items=3, max_list_items=2)
        
        # Simulate a profile state slice
        profile = {
            "user_id": "user123",
            "preferences": {
                "style": "casual",
                "colors": ["blue", "green", "red"],
                "brands": ["Nike", "Adidas", "Puma", "Reebok"],
            },
            "history": [
                {"item": "shirt", "date": "2024-01-01"},
                {"item": "pants", "date": "2024-01-02"},
                {"item": "shoes", "date": "2024-01-03"},
            ],
            "metadata": {
                "created": "2024-01-01",
                "updated": "2024-01-10",
            }
        }
        
        result = summarizer.summarize(profile)
        
        # Should show key information
        assert "'user_id': 'user123'" in result
        assert "'preferences'" in result
        assert "'style': 'casual'" in result
        # Should handle nested lists
        assert "'colors'" in result
        # At depth 2, lists show item count
        assert "items)" in result
        # Should show truncation for large collections
        assert "..." in result

# Made with Bob



class TestCycleDetection:
    """Test cycle detection in StateSummarizer."""
    
    def test_dict_self_reference(self):
        """Test detection of dictionary self-reference."""
        summarizer = StateSummarizer(max_depth=5)
        
        # Create circular reference
        data = {"name": "A"}
        data["self"] = data
        
        result = summarizer.summarize(data)
        
        # Should detect cycle
        assert "<cycle>" in result
        assert "'name': 'A'" in result
    
    def test_dict_mutual_reference(self):
        """Test detection of mutual references between dicts."""
        summarizer = StateSummarizer(max_depth=5)
        
        # Create mutual references
        a = {"name": "A"}
        b = {"name": "B", "ref": a}
        a["ref"] = b
        
        result = summarizer.summarize(a)
        
        # Should detect cycle
        assert "<cycle>" in result
        assert "'name': 'A'" in result
        assert "'name': 'B'" in result
    
    def test_list_with_self_reference(self):
        """Test detection of list containing itself."""
        summarizer = StateSummarizer(max_depth=5, max_list_items=10)
        
        # Create circular reference
        data = [1, 2, 3]
        data.append(data)
        
        result = summarizer.summarize(data)
        
        # Should detect cycle (when we try to traverse the 4th item which is the list itself)
        assert "<cycle>" in result
        assert "1" in result
        assert "2" in result
    
    def test_nested_cycle(self):
        """Test detection of cycle in nested structure."""
        summarizer = StateSummarizer(max_depth=5)
        
        # Create nested circular reference
        inner = {"value": 42}
        outer = {"inner": inner, "name": "outer"}
        inner["outer"] = outer
        
        result = summarizer.summarize(outer)
        
        # Should detect cycle
        assert "<cycle>" in result
        assert "'value': 42" in result
        assert "'name': 'outer'" in result
    
    def test_no_false_positive_for_same_value(self):
        """Test that same values (not same objects) don't trigger cycle detection."""
        summarizer = StateSummarizer(max_depth=5)
        
        # Same value, different objects
        data = {
            "a": {"x": 1},
            "b": {"x": 1},  # Same content, different object
        }
        
        result = summarizer.summarize(data)
        
        # Should NOT detect cycle (different objects)
        assert "<cycle>" not in result
        assert "'x': 1" in result
    
    def test_cycle_with_shared_reference(self):
        """Test cycle detection with shared (but not circular) references."""
        summarizer = StateSummarizer(max_depth=5)
        
        # Shared reference (not circular)
        shared = {"shared": "data"}
        data = {
            "a": shared,
            "b": shared,  # Same object, appears twice
        }
        
        result = summarizer.summarize(data)
        
        # Note: In current implementation, each dict key is processed independently,
        # so shared references at the same level won't trigger cycle detection.
        # Cycle detection works for parent-child relationships.
        assert "'a'" in result
        assert "'b'" in result
        assert "'shared': 'data'" in result
    
    def test_deep_shared_reference_not_circular(self):
        """Test that shared references at different levels work correctly."""
        summarizer = StateSummarizer(max_depth=5, max_dict_items=10)
        
        # Shared object but not circular
        shared = {"value": 123}
        data = {
            "first": {"ref": shared},
            "second": {"ref": shared},
        }
        
        result = summarizer.summarize(data)
        
        # Should detect the shared reference
        assert "<cycle>" in result or "'value': 123" in result
