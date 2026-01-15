import pytest
import yaml
from agent_contracts.config import load_config, get_config, set_config, FrameworkConfig
from pydantic import ValidationError

@pytest.fixture
def clean_config():
    """Reset the global config before and after each test."""
    set_config(None)
    yield
    set_config(None)

class TestConfig:
    def test_load_valid_config(self, tmp_path, clean_config):
        """Test loading a valid YAML configuration."""
        config_data = {
            "supervisor": {"max_iterations": 20},
            "response_types": {"terminal_states": ["done", "error"]},
            "features": {
                "orders": {"max_turns": 5, "max_items": 3}
            }
        }
        
        config_file = tmp_path / "agent_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
            
        config = load_config(str(config_file))
        set_config(config)
        
        current_config = get_config()
        
        assert current_config.supervisor.max_iterations == 20
        assert current_config.supervisor.terminal_response_types == ["done", "error"]
        assert current_config.features["orders"].max_turns == 5

    def test_load_nonexistent_file(self, clean_config):
        """Test error when loading missing file."""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent_config.yaml")

    def test_get_default_config(self, clean_config):
        """Test that get_config returns default when not loaded."""
        config = get_config()
        assert isinstance(config, FrameworkConfig)
        assert config.supervisor.max_iterations == 10  # Default value

    def test_invalid_schema(self, tmp_path, clean_config):
        """Test validation error for invalid config schema."""
        config_data = {
            "supervisor": {"max_iterations": "invalid_integer"}
        }
        
        config_file = tmp_path / "bad_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
            
        with pytest.raises(ValidationError):
            load_config(str(config_file))
