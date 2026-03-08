import pytest
from unittest.mock import AsyncMock, MagicMock

from src.llm.base import LLMClient


def test_llm_interface_is_abstract():
    with pytest.raises(TypeError):
        LLMClient()


@pytest.mark.asyncio
async def test_anthropic_client_complete():
    from src.llm.anthropic import AnthropicLLMClient

    mock_content = MagicMock()
    mock_content.text = "This is a response"
    mock_message = MagicMock()
    mock_message.content = [mock_content]

    client = AnthropicLLMClient(api_key="test-key")
    client._client = MagicMock()
    client._client.messages.create = AsyncMock(return_value=mock_message)

    result = await client.complete("Hello", system="Be helpful")
    assert result == "This is a response"
    client._client.messages.create.assert_called_once()


@pytest.mark.asyncio
async def test_anthropic_client_complete_json():
    from src.llm.anthropic import AnthropicLLMClient

    mock_content = MagicMock()
    mock_content.text = '{"category": "music", "family_score": 0.8}'
    mock_message = MagicMock()
    mock_message.content = [mock_content]

    client = AnthropicLLMClient(api_key="test-key")
    client._client = MagicMock()
    client._client.messages.create = AsyncMock(return_value=mock_message)

    result = await client.complete_json("Classify this event")
    assert result["category"] == "music"
    assert result["family_score"] == 0.8


@pytest.mark.asyncio
async def test_anthropic_client_strips_markdown_fences():
    from src.llm.anthropic import AnthropicLLMClient

    mock_content = MagicMock()
    mock_content.text = '```json\n{"key": "value"}\n```'
    mock_message = MagicMock()
    mock_message.content = [mock_content]

    client = AnthropicLLMClient(api_key="test-key")
    client._client = MagicMock()
    client._client.messages.create = AsyncMock(return_value=mock_message)

    result = await client.complete_json("test")
    assert result["key"] == "value"
