"""Configuration schema definitions.

Pydantic-based configuration models for the framework.
"""
from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class SupervisorConfig(BaseModel):
    """Supervisor configuration."""
    max_iterations: int = 10
    terminal_response_types: List[str] = Field(default_factory=list)


class FeatureConfig(BaseModel):
    """Generic feature configuration.
    
    Allows applications to define custom configuration for their features.
    The framework does not prescribe specific fields - applications can
    extend this or use any fields supported by their features.
    
    Example:
        class MyFeatureConfig(FeatureConfig):
            max_retries: int = 3
            timeout_seconds: float = 30.0
    """
    # Generic fields that can be overridden
    max_turns: int = Field(default=10, description="Maximum turns/iterations")
    max_items: int = Field(default=5, description="Maximum items to process")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Custom configuration")


class FrameworkConfig(BaseModel):
    """Framework-wide configuration.
    
    Can be loaded from YAML.
    
    Example:
        config = FrameworkConfig(
            supervisor=SupervisorConfig(max_iterations=10),
        )
        set_config(config)
    """
    supervisor: SupervisorConfig = Field(default_factory=SupervisorConfig)
    features: Dict[str, FeatureConfig] = Field(default_factory=dict)
