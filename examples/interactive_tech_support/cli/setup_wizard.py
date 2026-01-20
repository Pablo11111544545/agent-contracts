"""LLM setup wizard for the tech support CLI."""

import os
from dataclasses import dataclass
from typing import Any

from examples.interactive_tech_support.config.loader import AppConfig, LLMProviderConfig


@dataclass
class LLMConfiguration:
    """Configuration for an LLM provider."""

    provider: str
    api_key: str | None
    model: str
    azure_endpoint: str | None = None
    azure_api_version: str | None = None


class SetupWizard:
    """Interactive setup wizard for LLM configuration."""

    def __init__(self, config: AppConfig):
        """Initialize the setup wizard.

        Args:
            config: Application configuration with provider definitions.
        """
        self.config = config
        self.providers = config.providers

    def run(self) -> LLMConfiguration | None:
        """Run the setup wizard.

        Returns:
            LLM configuration if setup was successful, None if skipped.
        """
        print()
        print("=" * 50)
        print("LLM Provider Setup")
        print("=" * 50)
        print()
        print("Setting up an LLM enables smarter routing for")
        print("ambiguous questions. You can skip this and use")
        print("rule-based routing only.")
        print()

        # Check for existing environment variables
        existing = self._check_existing_config()
        if existing:
            use_existing = self._prompt_yes_no(
                f"Found existing {existing} configuration. Use it? [Y/n]", default=True
            )
            if use_existing:
                return self._configure_from_env(existing)

        # Ask if user wants to set up LLM
        setup_llm = self._prompt_yes_no(
            "Would you like to set up an LLM provider? [y/N]", default=False
        )

        if not setup_llm:
            print("Skipping LLM setup. Using rule-based routing only.")
            return None

        # Select provider
        provider_id = self._select_provider()
        if not provider_id:
            return None

        provider_config = self.providers.get(provider_id)
        if not provider_config:
            print(f"Unknown provider: {provider_id}")
            return None

        # Configure the selected provider
        return self._configure_provider(provider_id, provider_config)

    def _check_existing_config(self) -> str | None:
        """Check for existing LLM configuration in environment.

        Returns:
            Provider ID if found, None otherwise.
        """
        for provider_id, provider_config in self.providers.items():
            if provider_config.env_var:
                if os.environ.get(provider_config.env_var):
                    return provider_id
            elif provider_config.env_vars:
                api_key_var = provider_config.env_vars.get("api_key", "")
                if api_key_var and os.environ.get(api_key_var):
                    return provider_id
        return None

    def _configure_from_env(self, provider_id: str) -> LLMConfiguration | None:
        """Configure LLM from existing environment variables.

        Args:
            provider_id: The provider to configure.

        Returns:
            LLM configuration if successful, None otherwise.
        """
        provider_config = self.providers.get(provider_id)
        if not provider_config:
            return None

        # Get API key
        api_key = None
        azure_endpoint = None
        azure_api_version = None

        if provider_config.env_var:
            api_key = os.environ.get(provider_config.env_var)
        elif provider_config.env_vars:
            api_key = os.environ.get(provider_config.env_vars.get("api_key", ""))
            azure_endpoint = os.environ.get(provider_config.env_vars.get("endpoint", ""))
            azure_api_version = os.environ.get(
                provider_config.env_vars.get("api_version", ""),
                provider_config.default_api_version,
            )

        # Select model
        model = self._select_model(provider_config)
        if not model:
            model = provider_config.default_model

        print(f"Using {provider_config.name} with model: {model}")

        return LLMConfiguration(
            provider=provider_id,
            api_key=api_key,
            model=model,
            azure_endpoint=azure_endpoint,
            azure_api_version=azure_api_version,
        )

    def _select_provider(self) -> str | None:
        """Prompt user to select an LLM provider.

        Returns:
            Selected provider ID, or None if cancelled.
        """
        print()
        print("Select LLM Provider:")
        print()

        provider_list = list(self.providers.items())
        for i, (provider_id, provider_config) in enumerate(provider_list, 1):
            print(f"  {i}. {provider_config.name}")

        print()
        print("  0. Cancel")
        print()

        while True:
            try:
                choice = input("Choice [0-{}]: ".format(len(provider_list))).strip()
                if not choice:
                    continue

                choice_num = int(choice)
                if choice_num == 0:
                    return None
                if 1 <= choice_num <= len(provider_list):
                    return provider_list[choice_num - 1][0]

                print(f"Please enter a number between 0 and {len(provider_list)}")
            except ValueError:
                print("Please enter a valid number")
            except (EOFError, KeyboardInterrupt):
                return None

    def _configure_provider(
        self, provider_id: str, provider_config: LLMProviderConfig
    ) -> LLMConfiguration | None:
        """Configure a specific provider.

        Args:
            provider_id: The provider ID.
            provider_config: The provider configuration.

        Returns:
            LLM configuration if successful, None otherwise.
        """
        print()
        print(f"Configuring {provider_config.name}...")
        print()

        # Handle Ollama (local) specially
        if provider_id == "ollama":
            model = self._select_model(provider_config)
            if not model:
                model = provider_config.default_model

            print(f"Selected model: {model}")
            print("Note: Make sure Ollama is running locally.")

            return LLMConfiguration(
                provider=provider_id,
                api_key=None,
                model=model,
            )

        # Get API key
        api_key = self._get_api_key(provider_config)
        if not api_key:
            print("API key is required.")
            return None

        # Handle Azure OpenAI specially
        azure_endpoint = None
        azure_api_version = None

        if provider_id == "azure_openai":
            azure_endpoint = self._get_input(
                "Enter Azure OpenAI endpoint URL: ",
                required=True,
            )
            if not azure_endpoint:
                return None

            azure_api_version = self._get_input(
                f"Enter API version [{provider_config.default_api_version}]: ",
                default=provider_config.default_api_version,
            )

        # Select model
        model = self._select_model(provider_config)
        if not model:
            model = provider_config.default_model

        print()
        print(f"Configuration complete: {provider_config.name} - {model}")

        return LLMConfiguration(
            provider=provider_id,
            api_key=api_key,
            model=model,
            azure_endpoint=azure_endpoint,
            azure_api_version=azure_api_version,
        )

    def _get_api_key(self, provider_config: LLMProviderConfig) -> str | None:
        """Get API key from user.

        Args:
            provider_config: The provider configuration.

        Returns:
            The API key, or None if not provided.
        """
        env_var = provider_config.env_var
        if provider_config.env_vars:
            env_var = provider_config.env_vars.get("api_key", "")

        # Check environment first
        if env_var:
            env_value = os.environ.get(env_var)
            if env_value:
                use_env = self._prompt_yes_no(
                    f"Found API key in {env_var}. Use it? [Y/n]",
                    default=True,
                )
                if use_env:
                    return env_value

        # Prompt for API key
        print(f"Enter your {provider_config.name} API key")
        if env_var:
            print("(or configure the API key via an environment variable)")

        try:
            # Try to use getpass for hidden input
            import getpass

            api_key = getpass.getpass("API Key: ").strip()
        except Exception:
            api_key = input("API Key: ").strip()

        return api_key if api_key else None

    def _select_model(self, provider_config: LLMProviderConfig) -> str | None:
        """Prompt user to select a model.

        Args:
            provider_config: The provider configuration.

        Returns:
            Selected model name, or None for default.
        """
        models = provider_config.models
        default_model = provider_config.default_model

        if not models:
            return default_model

        print()
        print("Select model:")
        print()

        for i, model in enumerate(models, 1):
            default_marker = " (default)" if model == default_model else ""
            print(f"  {i}. {model}{default_marker}")

        print()

        while True:
            try:
                choice = input(f"Choice [1-{len(models)}] (Enter for default): ").strip()
                if not choice:
                    return default_model

                choice_num = int(choice)
                if 1 <= choice_num <= len(models):
                    return models[choice_num - 1]

                print(f"Please enter a number between 1 and {len(models)}")
            except ValueError:
                print("Please enter a valid number")
            except (EOFError, KeyboardInterrupt):
                return default_model

    def _prompt_yes_no(self, prompt: str, default: bool = False) -> bool:
        """Prompt for a yes/no response.

        Args:
            prompt: The prompt to display.
            default: Default value if empty input.

        Returns:
            True for yes, False for no.
        """
        try:
            response = input(prompt + " ").strip().lower()
            if not response:
                return default
            return response in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return default

    def _get_input(
        self,
        prompt: str,
        required: bool = False,
        default: str | None = None,
    ) -> str | None:
        """Get input from the user.

        Args:
            prompt: The prompt to display.
            required: Whether input is required.
            default: Default value if empty input.

        Returns:
            The user's input, or default value.
        """
        try:
            value = input(prompt).strip()
            if not value:
                if default:
                    return default
                if required:
                    print("This field is required.")
                    return self._get_input(prompt, required, default)
                return None
            return value
        except (EOFError, KeyboardInterrupt):
            return default
