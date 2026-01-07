"""Question schema definitions.

Pydantic models for question definitions.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class QuestionOption(BaseModel):
    """Question choice option."""
    label: str
    value: str


class QuestionDefinition(BaseModel):
    """Question definition schema (generic).
    
    Used for defining structured questions in YAML.
    
    Example YAML:
        my_question:
          id: my_question
          text: "What is your preference?"
          input_type: single_choice
          options:
            - { label: "Option A", value: "a" }
            - { label: "Option B", value: "b" }
    """
    id: str
    text: str
    input_type: Literal["single_choice", "multi_choice", "text", "image_upload"]
    options: list[QuestionOption] = Field(default_factory=list)
    placeholder: str | None = None


# Type aliases
QuestionGroup = dict[str, QuestionDefinition]
QuestionsConfig = dict[str, QuestionGroup]
