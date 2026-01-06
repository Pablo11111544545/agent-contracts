"""Configuration schema definitions.

Pydantic-based configuration models for the framework.
"""
from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel, Field


class SupervisorConfig(BaseModel):
    """Supervisor configuration."""
    max_iterations: int = 10
    terminal_response_types: List[str] = Field(default_factory=list)


class InterviewConfig(BaseModel):
    """Interview configuration."""
    max_turns: int = 10
    max_questions: int = 5


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
    interview: Dict[str, InterviewConfig] = Field(default_factory=dict)
