import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

@pytest.fixture
def mock_llm():
    """Fixture to provide a mock LLM."""
    llm = MagicMock(spec=BaseChatModel)
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="Mocked response"))
    return llm

@pytest.fixture
def mock_context():
    """Fixture to provide a basic context dictionary."""
    return {
        "user_id": "test_user",
        "session_id": "test_session",
    }
