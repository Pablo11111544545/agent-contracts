"""Tests for config loader and questions."""

import pytest
import tempfile
from pathlib import Path

from agent_contracts.config.loader import (
    load_config,
    set_config,
    get_config,
    load_questions,
    set_questions,
    get_question_group,
    get_question,
)
from agent_contracts.config.schema import FrameworkConfig


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self):
        """Test loading a valid config file."""
        yaml_content = """
supervisor:
  max_iterations: 15

response_types:
  terminal_states:
    - completed
    - error

features:
  order_processor:
    max_turns: 5
    max_items: 3
"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml_content)
            f.flush()
            
            config = load_config(f.name)
            
            assert config.supervisor.max_iterations == 15
            assert "completed" in config.supervisor.terminal_response_types
            assert "order_processor" in config.features
            assert config.features["order_processor"].max_turns == 5
            
            Path(f.name).unlink()

    def test_load_empty_config(self):
        """Test loading an empty config file."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write("")
            f.flush()
            
            config = load_config(f.name)
            
            # Should return defaults
            assert config.supervisor.max_iterations == 10
            assert config.supervisor.terminal_response_types == []
            
            Path(f.name).unlink()

    def test_load_partial_config(self):
        """Test loading a config with only some fields."""
        yaml_content = """
supervisor:
  max_iterations: 20
"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml_content)
            f.flush()
            
            config = load_config(f.name)
            
            assert config.supervisor.max_iterations == 20
            assert config.supervisor.terminal_response_types == []
            
            Path(f.name).unlink()


class TestSetGetConfig:
    """Tests for set_config and get_config."""

    def test_set_and_get_config(self):
        """Test setting and getting config."""
        from agent_contracts.config.schema import SupervisorConfig
        
        config = FrameworkConfig(
            supervisor=SupervisorConfig(max_iterations=25)
        )
        
        set_config(config)
        result = get_config()
        
        assert result.supervisor.max_iterations == 25
        
        # Cleanup
        set_config(None)

    def test_get_config_returns_default_when_not_set(self):
        """Test get_config returns default when not set."""
        set_config(None)
        
        result = get_config()
        
        assert isinstance(result, FrameworkConfig)
        assert result.supervisor.max_iterations == 10


class TestLoadQuestions:
    """Tests for load_questions function."""

    def test_load_valid_questions(self):
        """Test loading valid questions file."""
        yaml_content = """
shopping:
  q1:
    id: q1
    text: "What style do you prefer?"
    input_type: "single_choice"
    options:
      - { label: "Casual", value: "casual" }
      - { label: "Formal", value: "formal" }
  q2:
    id: q2
    text: "What is your budget?"
    input_type: "text"
"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml_content)
            f.flush()
            
            questions = load_questions(f.name)
            
            assert "shopping" in questions
            assert "q1" in questions["shopping"]
            assert questions["shopping"]["q1"].text == "What style do you prefer?"
            assert questions["shopping"]["q1"].input_type == "single_choice"
            
            Path(f.name).unlink()

    def test_load_empty_questions(self):
        """Test loading empty questions file."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write("")
            f.flush()
            
            questions = load_questions(f.name)
            
            assert questions == {}
            
            Path(f.name).unlink()

    def test_load_invalid_structure(self):
        """Test loading file with invalid structure."""
        yaml_content = "just a string"
        
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml_content)
            f.flush()
            
            questions = load_questions(f.name)
            
            assert questions == {}
            
            Path(f.name).unlink()

    def test_load_with_invalid_group(self):
        """Test loading file with invalid group (not a dict)."""
        yaml_content = """
shopping: "not a dict"
"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml_content)
            f.flush()
            
            questions = load_questions(f.name)
            
            # Group should be skipped
            assert "shopping" not in questions
            
            Path(f.name).unlink()


class TestQuestionAccessors:
    """Tests for get_question_group and get_question."""

    def test_get_question_group(self):
        """Test getting a question group."""
        from agent_contracts.config.questions import QuestionDefinition
        
        questions = {
            "shopping": {
                "q1": QuestionDefinition(
                    id="q1",
                    text="Question 1",
                    input_type="single_choice",
                ),
            }
        }
        set_questions(questions)
        
        result = get_question_group("shopping")
        
        assert "q1" in result
        assert result["q1"].text == "Question 1"
        
        # Cleanup
        set_questions(None)

    def test_get_question_group_not_found(self):
        """Test getting a non-existent question group."""
        set_questions({})
        
        result = get_question_group("nonexistent")
        
        assert result == {}
        
        set_questions(None)

    def test_get_question_group_when_none(self):
        """Test getting question group when questions not set."""
        set_questions(None)
        
        result = get_question_group("any")
        
        assert result == {}

    def test_get_question(self):
        """Test getting a specific question."""
        from agent_contracts.config.questions import QuestionDefinition
        
        questions = {
            "shopping": {
                "q1": QuestionDefinition(
                    id="q1",
                    text="Question 1",
                    input_type="single_choice",
                ),
            }
        }
        set_questions(questions)
        
        result = get_question("shopping", "q1")
        
        assert result is not None
        assert result.text == "Question 1"
        
        set_questions(None)

    def test_get_question_not_found(self):
        """Test getting a non-existent question."""
        from agent_contracts.config.questions import QuestionDefinition
        
        questions = {
            "shopping": {
                "q1": QuestionDefinition(
                    id="q1",
                    text="Question 1",
                    input_type="single_choice",
                ),
            }
        }
        set_questions(questions)
        
        result = get_question("shopping", "nonexistent")
        
        assert result is None
        
        set_questions(None)
