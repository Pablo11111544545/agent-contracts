"""Configuration loader.

YAML-based configuration loading with caching.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from agent_contracts.config.schema import FrameworkConfig, SupervisorConfig, FeatureConfig
from agent_contracts.config.questions import QuestionDefinition, QuestionsConfig


# =============================================================================
# Framework Config
# =============================================================================

_config: FrameworkConfig | None = None


def load_config(path: Path | str) -> FrameworkConfig:
    """Load framework configuration from YAML.
    
    Args:
        path: Path to YAML config file
        
    Returns:
        FrameworkConfig instance
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    
    # Parse supervisor config
    supervisor_data = data.get("supervisor", {}) if isinstance(data, dict) else {}
    response_types = data.get("response_types", {}) if isinstance(data, dict) else {}
    supervisor = SupervisorConfig(
        max_iterations=supervisor_data.get("max_iterations", 10),
        terminal_response_types=response_types.get("terminal_states", []),
    )
    
    # Parse feature configs
    features_data = data.get("features", {}) if isinstance(data, dict) else {}
    
    features: dict[str, FeatureConfig] = {}
    for name, config in features_data.items():
        if isinstance(config, dict):
            features[name] = FeatureConfig(
                max_turns=config.get("max_turns", 10),
                max_items=config.get("max_items", 5),
                extra=config.get("extra", {}),
            )
    
    return FrameworkConfig(
        supervisor=supervisor,
        features=features,
    )


def set_config(config: FrameworkConfig | None) -> None:
    """Set global framework configuration.
    
    Args:
        config: FrameworkConfig instance (or None to reset)
    """
    global _config
    _config = config


def get_config() -> FrameworkConfig:
    """Get current framework configuration.
    
    Returns:
        Current FrameworkConfig (or default if not set)
    """
    return _config or FrameworkConfig()


# =============================================================================
# Questions Config
# =============================================================================

_questions: QuestionsConfig | None = None


def load_questions(path: Path | str) -> QuestionsConfig:
    """Load questions configuration from YAML.
    
    Args:
        path: Path to questions YAML file
        
    Returns:
        QuestionsConfig (dict of question groups)
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    
    # Validate with Pydantic
    result: QuestionsConfig = {}
    if not isinstance(data, dict):
        return {}

    for group_name, questions in data.items():
        if not isinstance(questions, dict):
            continue
        result[group_name] = {}
        for qid, qdef in questions.items():
            if isinstance(qdef, dict):
                result[group_name][qid] = QuestionDefinition(**qdef)
    
    return result


def set_questions(config: QuestionsConfig) -> None:
    """Set global questions configuration.
    
    Args:
        config: QuestionsConfig instance
    """
    global _questions
    _questions = config


def get_question_group(group_name: str) -> dict[str, QuestionDefinition]:
    """Get a question group by name.
    
    Args:
        group_name: Name of the question group
        
    Returns:
        Dict of question ID -> QuestionDefinition
    """
    if _questions is None:
        return {}
    return _questions.get(group_name, {})


def get_question(group_name: str, question_id: str) -> QuestionDefinition | None:
    """Get a specific question.
    
    Args:
        group_name: Name of the question group
        question_id: Question ID
        
    Returns:
        QuestionDefinition or None if not found
    """
    group = get_question_group(group_name)
    return group.get(question_id)
