"""Factory for creating LLM instances based on provider configuration."""

from dataclasses import dataclass
from typing import Any


@dataclass
class AzureConfig:
    """Azure OpenAI specific configuration."""

    endpoint: str
    api_version: str = "2024-08-01-preview"


class LLMFactory:
    """Factory for creating LLM instances based on provider configuration.

    Supports multiple LLM providers:
    - OpenAI
    - Azure OpenAI
    - Anthropic
    - Google AI
    - Ollama (local)
    """

    @staticmethod
    def create(
        provider: str,
        api_key: str | None = None,
        model: str | None = None,
        azure_endpoint: str | None = None,
        azure_api_version: str | None = None,
    ) -> Any:
        """Create an LLM instance for the specified provider.

        Args:
            provider: The provider name (openai, azure_openai, anthropic, google, ollama).
            api_key: API key for the provider (not needed for ollama).
            model: Model name to use.
            azure_endpoint: Azure OpenAI endpoint (required for azure_openai).
            azure_api_version: Azure OpenAI API version.

        Returns:
            A LangChain chat model instance.

        Raises:
            ValueError: If provider is unknown or required config is missing.
            ImportError: If the required LangChain provider library is not installed.
        """
        if provider == "openai":
            return LLMFactory._create_openai(api_key, model)
        elif provider == "azure_openai":
            return LLMFactory._create_azure_openai(
                api_key, model, azure_endpoint, azure_api_version
            )
        elif provider == "anthropic":
            return LLMFactory._create_anthropic(api_key, model)
        elif provider == "google":
            return LLMFactory._create_google(api_key, model)
        elif provider == "ollama":
            return LLMFactory._create_ollama(model)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    @staticmethod
    def _create_openai(api_key: str | None, model: str | None) -> Any:
        """Create an OpenAI chat model.

        Args:
            api_key: OpenAI API key.
            model: Model name.

        Returns:
            ChatOpenAI instance.
        """
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as e:
            raise ImportError(
                "langchain-openai is required for OpenAI support. "
                "Install with: pip install langchain-openai"
            ) from e

        return ChatOpenAI(
            api_key=api_key,
            model=model or "gpt-4o-mini",
        )

    @staticmethod
    def _create_azure_openai(
        api_key: str | None,
        model: str | None,
        endpoint: str | None,
        api_version: str | None,
    ) -> Any:
        """Create an Azure OpenAI chat model.

        Args:
            api_key: Azure OpenAI API key.
            model: Deployment name.
            endpoint: Azure OpenAI endpoint URL.
            api_version: API version.

        Returns:
            AzureChatOpenAI instance.
        """
        try:
            from langchain_openai import AzureChatOpenAI
        except ImportError as e:
            raise ImportError(
                "langchain-openai is required for Azure OpenAI support. "
                "Install with: pip install langchain-openai"
            ) from e

        if not endpoint:
            raise ValueError("Azure OpenAI requires an endpoint URL")

        return AzureChatOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version or "2024-08-01-preview",
            azure_deployment=model or "gpt-4o-mini",
        )

    @staticmethod
    def _create_anthropic(api_key: str | None, model: str | None) -> Any:
        """Create an Anthropic chat model.

        Args:
            api_key: Anthropic API key.
            model: Model name.

        Returns:
            ChatAnthropic instance.
        """
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as e:
            raise ImportError(
                "langchain-anthropic is required for Anthropic support. "
                "Install with: pip install langchain-anthropic"
            ) from e

        return ChatAnthropic(
            api_key=api_key,
            model=model or "claude-sonnet-4-20250514",
        )

    @staticmethod
    def _create_google(api_key: str | None, model: str | None) -> Any:
        """Create a Google AI chat model.

        Args:
            api_key: Google API key.
            model: Model name.

        Returns:
            ChatGoogleGenerativeAI instance.
        """
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as e:
            raise ImportError(
                "langchain-google-genai is required for Google AI support. "
                "Install with: pip install langchain-google-genai"
            ) from e

        return ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=model or "gemini-1.5-flash",
        )

    @staticmethod
    def _create_ollama(model: str | None) -> Any:
        """Create an Ollama chat model.

        Args:
            model: Model name.

        Returns:
            ChatOllama instance.
        """
        try:
            from langchain_ollama import ChatOllama
        except ImportError as e:
            raise ImportError(
                "langchain-ollama is required for Ollama support. "
                "Install with: pip install langchain-ollama"
            ) from e

        return ChatOllama(
            model=model or "llama3.1",
        )
