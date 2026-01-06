"""JSON utilities.

Provides datetime-aware JSON serialization.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def json_serializer(obj: Any) -> str:
    """Serialize non-JSON objects like datetime.
    
    Args:
        obj: Object to serialize
        
    Returns:
        Serialized string
        
    Raises:
        TypeError: If object cannot be serialized
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def json_dumps(obj: Any, **kwargs) -> str:
    """JSON dumps with datetime support.
    
    Args:
        obj: Object to serialize to JSON
        **kwargs: Additional arguments for json.dumps
        
    Returns:
        JSON string
    """
    kwargs.setdefault("ensure_ascii", False)
    kwargs.setdefault("default", json_serializer)
    return json.dumps(obj, **kwargs)
