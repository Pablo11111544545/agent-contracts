"""Logging utilities.

Provides abstracted logging compatible with standard logging and structlog.
"""
from __future__ import annotations

import logging
from typing import Any


def get_logger(name: str = "agent_contracts", **context: Any) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name
        **context: Additional context (for structlog compatibility)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def configure_logging(
    level: int = logging.INFO,
    format_string: str = "%(levelname)s - %(name)s - %(message)s",
) -> None:
    """Configure logging.
    
    Args:
        level: Logging level
        format_string: Log format string
    """
    logging.basicConfig(level=level, format=format_string)


# Optional structlog integration
try:
    import structlog
    _HAS_STRUCTLOG = True
except ImportError:
    _HAS_STRUCTLOG = False


def get_structured_logger(name: str = "agent_contracts", **context: Any):
    """Get a structlog logger if available, otherwise standard logger.
    
    Args:
        name: Logger name
        **context: Bound context for structlog
        
    Returns:
        Logger instance (structlog or standard)
    """
    if _HAS_STRUCTLOG:
        return structlog.get_logger(name).bind(**context)
    return get_logger(name)
