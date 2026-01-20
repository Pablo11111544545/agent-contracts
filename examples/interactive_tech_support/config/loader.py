"""Configuration loader for the tech support demo."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SupervisorConfig:
    """Supervisor configuration."""

    max_iterations: int = 10


@dataclass
class IOConfig:
    """IO configuration."""

    strict: bool = False
    warn: bool = True
    drop_undeclared_writes: bool = True


@dataclass
class ResponseTypesConfig:
    """Response types configuration."""

    terminal_states: list[str] = field(
        default_factory=lambda: ["answer", "error", "goodbye"]
    )


@dataclass
class TechSupportConfig:
    """Tech support feature configuration."""

    max_turns: int = 20
    max_clarifications: int = 3


@dataclass
class FeaturesConfig:
    """Features configuration."""

    tech_support: TechSupportConfig = field(default_factory=TechSupportConfig)


@dataclass
class LLMProviderConfig:
    """LLM provider configuration."""

    name: str
    models: list[str]
    default_model: str
    env_var: str | None = None
    env_vars: dict[str, str] | None = None
    base_url: str | None = None
    default_api_version: str | None = None


@dataclass
class AppConfig:
    """Main application configuration."""

    supervisor: SupervisorConfig = field(default_factory=SupervisorConfig)
    io: IOConfig = field(default_factory=IOConfig)
    response_types: ResponseTypesConfig = field(default_factory=ResponseTypesConfig)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    providers: dict[str, LLMProviderConfig] = field(default_factory=dict)


class ConfigLoader:
    """Load configuration from YAML files."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize the config loader.

        Args:
            config_dir: Directory containing configuration files.
                       Defaults to the config directory in this package.
        """
        if config_dir is None:
            config_dir = Path(__file__).parent
        self.config_dir = config_dir

    def load(self) -> AppConfig:
        """Load all configuration files.

        Returns:
            The complete application configuration.
        """
        settings = self._load_yaml("settings.yaml")
        providers = self._load_yaml("llm_providers.yaml")

        # Parse supervisor config
        supervisor_data = settings.get("supervisor", {})
        supervisor = SupervisorConfig(
            max_iterations=supervisor_data.get("max_iterations", 10)
        )

        # Parse IO config
        io_data = settings.get("io", {})
        io_config = IOConfig(
            strict=io_data.get("strict", False),
            warn=io_data.get("warn", True),
            drop_undeclared_writes=io_data.get("drop_undeclared_writes", True),
        )

        # Parse response types config
        response_data = settings.get("response_types", {})
        response_types = ResponseTypesConfig(
            terminal_states=response_data.get(
                "terminal_states", ["answer", "error", "goodbye"]
            )
        )

        # Parse features config
        features_data = settings.get("features", {})
        tech_support_data = features_data.get("tech_support", {})
        tech_support = TechSupportConfig(
            max_turns=tech_support_data.get("max_turns", 20),
            max_clarifications=tech_support_data.get("max_clarifications", 3),
        )
        features = FeaturesConfig(tech_support=tech_support)

        # Parse providers config
        providers_dict: dict[str, LLMProviderConfig] = {}
        providers_data = providers.get("providers", {})
        for provider_id, provider_data in providers_data.items():
            providers_dict[provider_id] = LLMProviderConfig(
                name=provider_data.get("name", provider_id),
                models=provider_data.get("models", []),
                default_model=provider_data.get("default_model", ""),
                env_var=provider_data.get("env_var"),
                env_vars=provider_data.get("env_vars"),
                base_url=provider_data.get("base_url"),
                default_api_version=provider_data.get("default_api_version"),
            )

        return AppConfig(
            supervisor=supervisor,
            io=io_config,
            response_types=response_types,
            features=features,
            providers=providers_dict,
        )

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        """Load a YAML file.

        Args:
            filename: Name of the YAML file to load.

        Returns:
            The parsed YAML data.
        """
        filepath = self.config_dir / filename
        if not filepath.exists():
            return {}
        with open(filepath) as f:
            return yaml.safe_load(f) or {}
