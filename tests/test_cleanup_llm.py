from unittest.mock import MagicMock, patch

import pytest

from mista_wispa.cleanup import llm_cleanup


@pytest.fixture
def mock_openai():
    with patch("mista_wispa.cleanup.OpenAI") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        choice = MagicMock()
        choice.message.content = "The meeting is at three PM tomorrow."
        client.chat.completions.create.return_value = MagicMock(choices=[choice])
        yield client


def test_llm_cleanup_calls_api(mock_openai):
    result = llm_cleanup("the meeting is at three pm tomorrow", server_url="http://localhost:1234/v1")
    assert result == "The meeting is at three PM tomorrow."
    mock_openai.chat.completions.create.assert_called_once()


def test_llm_cleanup_sends_system_prompt(mock_openai):
    llm_cleanup("hello", server_url="http://localhost:1234/v1")
    call_args = mock_openai.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "preserve meaning" in messages[0]["content"].lower()


def test_llm_cleanup_returns_original_on_timeout():
    with patch("mista_wispa.cleanup.OpenAI") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        client.chat.completions.create.side_effect = Exception("timeout")
        result = llm_cleanup("original text", server_url="http://localhost:1234/v1")
    assert result == "original text"


def test_llm_cleanup_returns_original_on_empty_response():
    with patch("mista_wispa.cleanup.OpenAI") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        choice = MagicMock()
        choice.message.content = ""
        client.chat.completions.create.return_value = MagicMock(choices=[choice])
        result = llm_cleanup("original text", server_url="http://localhost:1234/v1")
    assert result == "original text"
