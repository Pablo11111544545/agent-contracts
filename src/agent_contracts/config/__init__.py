"""Config package - Configuration system."""

from agent_contracts.config.schema import (
    SupervisorConfig,
    FeatureConfig,
    FrameworkConfig,
)
from agent_contracts.config.loader import (
    load_config,
    set_config,
    get_config,
    load_questions,
    set_questions,
    get_question_group,
    get_question,
)
from agent_contracts.config.questions import (
    QuestionOption,
    QuestionDefinition,
)

__all__ = [
    # Schema
    "SupervisorConfig",
    "FeatureConfig",
    "FrameworkConfig",
    # Loader
    "load_config",
    "set_config",
    "get_config",
    "load_questions",
    "set_questions",
    "get_question_group",
    "get_question",
    # Questions
    "QuestionOption",
    "QuestionDefinition",
]
