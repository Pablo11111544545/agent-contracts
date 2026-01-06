"""Configuration schema definitions.

Pydantic-based configuration models for the framework.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SupervisorConfig:
    """Supervisor configuration."""
    max_iterations: int = 10
    terminal_response_types: list[str] = field(default_factory=list)


@dataclass
class InterviewConfig:
    """Interview configuration."""
    max_turns: int = 10
    max_questions: int = 5


@dataclass
class FrameworkConfig:
    """Framework-wide configuration.
    
    Can be loaded from YAML.
    
    Example:
        config = FrameworkConfig(
            supervisor=SupervisorConfig(max_iterations=10),
        )
        set_config(config)
    """
    supervisor: SupervisorConfig = field(default_factory=SupervisorConfig)
    interview: dict[str, InterviewConfig] = field(default_factory=dict)
