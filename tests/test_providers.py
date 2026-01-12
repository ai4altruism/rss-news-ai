# tests/test_providers.py

"""
Unit tests for the LLM provider abstraction layer.

Tests cover:
- Provider factory and configuration parsing
- OpenAI provider implementation
- Backward compatibility
- Error handling
"""

import pytest
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from providers import (
    get_provider,
    parse_model_config,
    list_providers,
    register_provider,
    BaseProvider,
    OpenAIProvider,
    XAIProvider,
    AnthropicProvider,
    GeminiProvider,
)


class TestParseModelConfig:
    """Tests for parse_model_config function."""

    def test_old_format_defaults_to_openai(self):
        """Old format without provider prefix should default to OpenAI."""
        provider, model = parse_model_config("gpt-4o-mini")
        assert provider == "openai"
        assert model == "gpt-4o-mini"

    def test_old_format_gpt5(self):
        """Old format with gpt-5 model should default to OpenAI."""
        provider, model = parse_model_config("gpt-5-mini")
        assert provider == "openai"
        assert model == "gpt-5-mini"

    def test_new_format_openai(self):
        """New format with explicit openai provider."""
        provider, model = parse_model_config("openai:gpt-4o-mini")
        assert provider == "openai"
        assert model == "gpt-4o-mini"

    def test_new_format_anthropic(self):
        """New format with anthropic provider."""
        provider, model = parse_model_config("anthropic:claude-sonnet-4-20250514")
        assert provider == "anthropic"
        assert model == "claude-sonnet-4-20250514"

    def test_new_format_google(self):
        """New format with google provider."""
        provider, model = parse_model_config("google:gemini-2.0-flash")
        assert provider == "google"
        assert model == "gemini-2.0-flash"

    def test_new_format_xai(self):
        """New format with xai provider."""
        provider, model = parse_model_config("xai:grok-3-mini")
        assert provider == "xai"
        assert model == "grok-3-mini"

    def test_provider_name_case_insensitive(self):
        """Provider name should be case insensitive."""
        provider, model = parse_model_config("OpenAI:gpt-4o-mini")
        assert provider == "openai"
        assert model == "gpt-4o-mini"

    def test_model_with_colons(self):
        """Model name can contain colons (only first colon splits)."""
        provider, model = parse_model_config("google:models/gemini-2.0-flash")
        assert provider == "google"
        assert model == "models/gemini-2.0-flash"


class TestListProviders:
    """Tests for list_providers function."""

    def test_openai_in_providers(self):
        """OpenAI should be in the list of providers."""
        providers = list_providers()
        assert "openai" in providers

    def test_returns_list(self):
        """Should return a list."""
        providers = list_providers()
        assert isinstance(providers, list)


class TestGetProvider:
    """Tests for get_provider factory function."""

    def test_get_openai_provider_old_format(self):
        """Get OpenAI provider using old format."""
        provider = get_provider("gpt-4o-mini", openai_api_key="test-key")
        assert isinstance(provider, OpenAIProvider)
        assert provider.get_provider_name() == "openai"
        assert provider.get_model_name() == "gpt-4o-mini"

    def test_get_openai_provider_new_format(self):
        """Get OpenAI provider using new format."""
        provider = get_provider("openai:gpt-4o-mini", openai_api_key="test-key")
        assert isinstance(provider, OpenAIProvider)
        assert provider.get_model_name() == "gpt-4o-mini"

    def test_missing_api_key_raises_error(self):
        """Missing API key should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_provider("gpt-4o-mini")
        assert "API key required" in str(exc_info.value)

    def test_unknown_provider_raises_error(self):
        """Unknown provider should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_provider("unknown:model", openai_api_key="test-key")
        assert "Unknown provider" in str(exc_info.value)
        assert "unknown" in str(exc_info.value)

    def test_provider_validates_config(self):
        """Provider should validate configuration."""
        provider = get_provider("gpt-4o-mini", openai_api_key="test-key")
        assert provider.validate_config() is True

    def test_provider_repr(self):
        """Provider should have useful repr."""
        provider = get_provider("gpt-4o-mini", openai_api_key="test-key")
        repr_str = repr(provider)
        assert "OpenAIProvider" in repr_str
        assert "gpt-4o-mini" in repr_str


class TestOpenAIProvider:
    """Tests for OpenAIProvider class."""

    def test_is_gpt5_model_true(self):
        """Should detect gpt-5 models."""
        provider = OpenAIProvider(model="gpt-5-mini", api_key="test-key")
        assert provider._is_gpt5_model() is True

    def test_is_gpt5_model_false(self):
        """Should not detect gpt-4 as gpt-5."""
        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")
        assert provider._is_gpt5_model() is False

    def test_provider_name(self):
        """Should return 'openai' as provider name."""
        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")
        assert provider.get_provider_name() == "openai"

    @patch('providers.openai_provider.requests.post')
    def test_complete_gpt4_includes_temperature(self, mock_post):
        """GPT-4 calls should include temperature."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Hello!"}]
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")
        result = provider.complete("Hello", temperature=0.5)

        # Check that temperature was included in the request
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        assert "temperature" in request_data
        assert request_data["temperature"] == 0.5
        assert "reasoning" not in request_data

    @patch('providers.openai_provider.requests.post')
    def test_complete_gpt5_no_temperature(self, mock_post):
        """GPT-5 calls should not include temperature."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "output": [
                {"type": "reasoning", "summary": []},
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Hello!"}]
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = OpenAIProvider(model="gpt-5-mini", api_key="test-key")
        result = provider.complete("Hello", temperature=0.5)

        # Check that temperature was NOT included, but reasoning was
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        assert "temperature" not in request_data
        assert "reasoning" in request_data
        assert request_data["reasoning"]["effort"] == "low"

    @patch('providers.openai_provider.requests.post')
    def test_complete_gpt5_higher_token_limit(self, mock_post):
        """GPT-5 calls should use higher token limit."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "output": [
                {"type": "reasoning", "summary": []},
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Hello!"}]
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = OpenAIProvider(model="gpt-5-mini", api_key="test-key")
        provider.complete("Hello", max_tokens=500)

        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        # Should be at least 4x or 4096
        assert request_data["max_output_tokens"] >= 2000

    @patch('providers.openai_provider.requests.post')
    def test_parse_response_gpt4_format(self, mock_post):
        """Should parse GPT-4 response format."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Hello world!"}]
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")
        result, usage = provider.complete("Hello")
        assert result == "Hello world!"

    @patch('providers.openai_provider.requests.post')
    def test_parse_response_gpt5_format(self, mock_post):
        """Should parse GPT-5 response format (with reasoning block)."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "output": [
                {"type": "reasoning", "summary": []},
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Hello from GPT-5!"}]
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = OpenAIProvider(model="gpt-5-mini", api_key="test-key")
        result, usage = provider.complete("Hello")
        assert result == "Hello from GPT-5!"

    @patch('providers.openai_provider.requests.post')
    def test_api_error_raises_exception(self, mock_post):
        """API errors should raise exceptions."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_post.return_value = mock_response

        provider = OpenAIProvider(model="gpt-4o-mini", api_key="bad-key")
        with pytest.raises(Exception):
            provider.complete("Hello")


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing code."""

    @patch('providers.openai_provider.requests.post')
    def test_call_responses_api_uses_provider(self, mock_post):
        """call_responses_api should use provider abstraction."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Response"}]
                }
            ]
        }
        mock_post.return_value = mock_response

        from utils import call_responses_api
        result = call_responses_api(
            model="gpt-4o-mini",
            prompt="Hello",
            openai_api_key="test-key",
            instructions="Be helpful",
            max_output_tokens=100,
            temperature=0.7,
        )

        assert result == "Response"
        # Verify the API was called
        assert mock_post.called

    @patch('providers.openai_provider.requests.post')
    def test_call_llm_with_old_format(self, mock_post):
        """call_llm should work with old format config."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Response"}]
                }
            ]
        }
        mock_post.return_value = mock_response

        from utils import call_llm
        result = call_llm(
            model_config="gpt-4o-mini",
            prompt="Hello",
            api_keys={"openai": "test-key"},
        )

        assert result == "Response"

    @patch('providers.openai_provider.requests.post')
    def test_call_llm_with_new_format(self, mock_post):
        """call_llm should work with new format config."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Response"}]
                }
            ]
        }
        mock_post.return_value = mock_response

        from utils import call_llm
        result = call_llm(
            model_config="openai:gpt-4o-mini",
            prompt="Hello",
            api_keys={"openai": "test-key"},
        )

        assert result == "Response"


class TestRegisterProvider:
    """Tests for provider registration."""

    def test_register_custom_provider(self):
        """Should be able to register a custom provider."""
        class CustomProvider(BaseProvider):
            def complete(self, prompt, instructions="", max_tokens=500, temperature=1.0):
                return "custom response"
            def get_provider_name(self):
                return "custom"

        register_provider("custom", CustomProvider)
        assert "custom" in list_providers()

        # Custom providers would need factory updates to handle their API keys
        # For now, just verify registration works

    def test_register_non_provider_fails(self):
        """Should fail to register non-provider class."""
        class NotAProvider:
            pass

        with pytest.raises(TypeError):
            register_provider("bad", NotAProvider)


class TestXAIProvider:
    """Tests for XAIProvider class."""

    def test_xai_in_providers_list(self):
        """xAI should be in the list of providers."""
        providers = list_providers()
        assert "xai" in providers

    def test_get_xai_provider(self):
        """Get xAI provider using new format."""
        provider = get_provider("xai:grok-3-mini", xai_api_key="test-key")
        assert isinstance(provider, XAIProvider)
        assert provider.get_provider_name() == "xai"
        assert provider.get_model_name() == "grok-3-mini"

    def test_xai_provider_name(self):
        """Should return 'xai' as provider name."""
        provider = XAIProvider(model="grok-3-mini", api_key="test-key")
        assert provider.get_provider_name() == "xai"

    def test_xai_missing_api_key_raises_error(self):
        """Missing xAI API key should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_provider("xai:grok-3-mini")
        assert "API key required" in str(exc_info.value)

    @patch('providers.xai_provider.requests.post')
    def test_complete_includes_temperature(self, mock_post):
        """xAI calls should include temperature."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello from Grok!"
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = XAIProvider(model="grok-3-mini", api_key="test-key")
        result = provider.complete("Hello", temperature=0.7)

        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        assert request_data["temperature"] == 0.7
        assert request_data["model"] == "grok-3-mini"

    @patch('providers.xai_provider.requests.post')
    def test_complete_with_instructions(self, mock_post):
        """xAI calls should include system message when instructions provided."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Response"
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = XAIProvider(model="grok-3-mini", api_key="test-key")
        provider.complete("Hello", instructions="Be helpful")

        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        messages = request_data["messages"]

        # Should have system message + user message
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "Be helpful"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"

    @patch('providers.xai_provider.requests.post')
    def test_complete_without_instructions(self, mock_post):
        """xAI calls without instructions should only have user message."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Response"
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = XAIProvider(model="grok-3-mini", api_key="test-key")
        provider.complete("Hello")

        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        messages = request_data["messages"]

        # Should only have user message
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    @patch('providers.xai_provider.requests.post')
    def test_parse_response(self, mock_post):
        """Should parse xAI chat completion response."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello from Grok!"
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = XAIProvider(model="grok-3-mini", api_key="test-key")
        result, usage = provider.complete("Hello")
        assert result == "Hello from Grok!"

    @patch('providers.xai_provider.requests.post')
    def test_api_error_raises_exception(self, mock_post):
        """API errors should raise exceptions."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_post.return_value = mock_response

        provider = XAIProvider(model="grok-3-mini", api_key="bad-key")
        with pytest.raises(Exception):
            provider.complete("Hello")

    @patch('providers.xai_provider.requests.post')
    def test_empty_choices_raises_error(self, mock_post):
        """Empty choices array should raise ValueError."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"choices": []}
        mock_post.return_value = mock_response

        provider = XAIProvider(model="grok-3-mini", api_key="test-key")
        with pytest.raises(ValueError) as exc_info:
            provider.complete("Hello")
        assert "No choices" in str(exc_info.value)

    @patch('providers.xai_provider.requests.post')
    def test_missing_content_raises_error(self, mock_post):
        """Missing content in response should raise ValueError."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant"
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = XAIProvider(model="grok-3-mini", api_key="test-key")
        with pytest.raises(ValueError) as exc_info:
            provider.complete("Hello")
        assert "No content" in str(exc_info.value)

    @patch('providers.xai_provider.requests.post')
    def test_uses_correct_api_url(self, mock_post):
        """Should use xAI API URL."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Hi"}}]
        }
        mock_post.return_value = mock_response

        provider = XAIProvider(model="grok-3-mini", api_key="test-key")
        provider.complete("Hello")

        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.x.ai/v1/chat/completions"

    @patch('providers.xai_provider.requests.post')
    def test_call_llm_with_xai(self, mock_post):
        """call_llm should work with xai provider."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Grok response"}}]
        }
        mock_post.return_value = mock_response

        from utils import call_llm
        result = call_llm(
            model_config="xai:grok-3-mini",
            prompt="Hello",
            api_keys={"xai": "test-key"},
        )

        assert result == "Grok response"


class TestAnthropicProvider:
    """Tests for AnthropicProvider class."""

    def test_anthropic_in_providers_list(self):
        """Anthropic should be in the list of providers."""
        providers = list_providers()
        assert "anthropic" in providers

    def test_get_anthropic_provider(self):
        """Get Anthropic provider using new format."""
        provider = get_provider("anthropic:claude-sonnet-4-20250514", anthropic_api_key="test-key")
        assert isinstance(provider, AnthropicProvider)
        assert provider.get_provider_name() == "anthropic"
        assert provider.get_model_name() == "claude-sonnet-4-20250514"

    def test_anthropic_provider_name(self):
        """Should return 'anthropic' as provider name."""
        provider = AnthropicProvider(model="claude-sonnet-4-20250514", api_key="test-key")
        assert provider.get_provider_name() == "anthropic"

    def test_anthropic_missing_api_key_raises_error(self):
        """Missing Anthropic API key should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_provider("anthropic:claude-sonnet-4-20250514")
        assert "API key required" in str(exc_info.value)

    @patch('providers.anthropic_provider.requests.post')
    def test_complete_with_system_prompt(self, mock_post):
        """Anthropic calls should use separate system parameter."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello from Claude!"}],
            "stop_reason": "end_turn"
        }
        mock_post.return_value = mock_response

        provider = AnthropicProvider(model="claude-sonnet-4-20250514", api_key="test-key")
        provider.complete("Hello", instructions="Be helpful")

        call_args = mock_post.call_args
        request_data = call_args[1]["json"]

        # System prompt should be separate, not in messages
        assert "system" in request_data
        assert request_data["system"] == "Be helpful"
        assert len(request_data["messages"]) == 1
        assert request_data["messages"][0]["role"] == "user"
        assert request_data["messages"][0]["content"] == "Hello"

    @patch('providers.anthropic_provider.requests.post')
    def test_complete_without_instructions(self, mock_post):
        """Anthropic calls without instructions should not have system parameter."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Response"}],
            "stop_reason": "end_turn"
        }
        mock_post.return_value = mock_response

        provider = AnthropicProvider(model="claude-sonnet-4-20250514", api_key="test-key")
        provider.complete("Hello")

        call_args = mock_post.call_args
        request_data = call_args[1]["json"]

        # Should not have system parameter
        assert "system" not in request_data

    @patch('providers.anthropic_provider.requests.post')
    def test_complete_includes_required_headers(self, mock_post):
        """Anthropic calls should include required headers."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Response"}],
            "stop_reason": "end_turn"
        }
        mock_post.return_value = mock_response

        provider = AnthropicProvider(model="claude-sonnet-4-20250514", api_key="test-key")
        provider.complete("Hello")

        call_args = mock_post.call_args
        headers = call_args[1]["headers"]

        assert headers["x-api-key"] == "test-key"
        assert "anthropic-version" in headers
        assert headers["Content-Type"] == "application/json"

    @patch('providers.anthropic_provider.requests.post')
    def test_temperature_clamped_to_valid_range(self, mock_post):
        """Temperature should be clamped to 0.0-1.0 for Anthropic."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Response"}],
            "stop_reason": "end_turn"
        }
        mock_post.return_value = mock_response

        provider = AnthropicProvider(model="claude-sonnet-4-20250514", api_key="test-key")

        # Test with temperature > 1.0
        provider.complete("Hello", temperature=1.5)
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        assert request_data["temperature"] == 1.0

    @patch('providers.anthropic_provider.requests.post')
    def test_parse_response(self, mock_post):
        """Should parse Anthropic Messages API response."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello from Claude!"}],
            "stop_reason": "end_turn"
        }
        mock_post.return_value = mock_response

        provider = AnthropicProvider(model="claude-sonnet-4-20250514", api_key="test-key")
        result, usage = provider.complete("Hello")
        assert result == "Hello from Claude!"

    @patch('providers.anthropic_provider.requests.post')
    def test_parse_response_multiple_text_blocks(self, mock_post):
        """Should concatenate multiple text blocks in response."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Part 1. "},
                {"type": "text", "text": "Part 2."}
            ],
            "stop_reason": "end_turn"
        }
        mock_post.return_value = mock_response

        provider = AnthropicProvider(model="claude-sonnet-4-20250514", api_key="test-key")
        result, usage = provider.complete("Hello")
        assert result == "Part 1. Part 2."

    @patch('providers.anthropic_provider.requests.post')
    def test_api_error_raises_exception(self, mock_post):
        """API errors should raise exceptions."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_post.return_value = mock_response

        provider = AnthropicProvider(model="claude-sonnet-4-20250514", api_key="bad-key")
        with pytest.raises(Exception):
            provider.complete("Hello")

    @patch('providers.anthropic_provider.requests.post')
    def test_empty_content_raises_error(self, mock_post):
        """Empty content array should raise ValueError."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [],
            "stop_reason": "end_turn"
        }
        mock_post.return_value = mock_response

        provider = AnthropicProvider(model="claude-sonnet-4-20250514", api_key="test-key")
        with pytest.raises(ValueError) as exc_info:
            provider.complete("Hello")
        assert "No content" in str(exc_info.value)

    @patch('providers.anthropic_provider.requests.post')
    def test_uses_correct_api_url(self, mock_post):
        """Should use Anthropic API URL."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hi"}],
            "stop_reason": "end_turn"
        }
        mock_post.return_value = mock_response

        provider = AnthropicProvider(model="claude-sonnet-4-20250514", api_key="test-key")
        provider.complete("Hello")

        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.anthropic.com/v1/messages"

    @patch('providers.anthropic_provider.requests.post')
    def test_call_llm_with_anthropic(self, mock_post):
        """call_llm should work with anthropic provider."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Claude response"}],
            "stop_reason": "end_turn"
        }
        mock_post.return_value = mock_response

        from utils import call_llm
        result = call_llm(
            model_config="anthropic:claude-sonnet-4-20250514",
            prompt="Hello",
            api_keys={"anthropic": "test-key"},
        )

        assert result == "Claude response"

    @patch('providers.anthropic_provider.requests.post')
    def test_max_tokens_required(self, mock_post):
        """Anthropic requires max_tokens in request."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Response"}],
            "stop_reason": "end_turn"
        }
        mock_post.return_value = mock_response

        provider = AnthropicProvider(model="claude-sonnet-4-20250514", api_key="test-key")
        provider.complete("Hello", max_tokens=1000)

        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        assert request_data["max_tokens"] == 1000


class TestGeminiProvider:
    """Tests for GeminiProvider class."""

    def test_google_in_providers_list(self):
        """Google should be in the list of providers."""
        providers = list_providers()
        assert "google" in providers

    def test_get_gemini_provider(self):
        """Get Gemini provider using new format."""
        provider = get_provider("google:gemini-2.0-flash", google_api_key="test-key")
        assert isinstance(provider, GeminiProvider)
        assert provider.get_provider_name() == "google"
        assert provider.get_model_name() == "gemini-2.0-flash"

    def test_gemini_provider_name(self):
        """Should return 'google' as provider name."""
        provider = GeminiProvider(model="gemini-2.0-flash", api_key="test-key")
        assert provider.get_provider_name() == "google"

    def test_gemini_missing_api_key_raises_error(self):
        """Missing Google API key should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_provider("google:gemini-2.0-flash")
        assert "API key required" in str(exc_info.value)

    def test_api_url_construction(self):
        """Should construct correct API URL."""
        provider = GeminiProvider(model="gemini-2.0-flash", api_key="test-key")
        url = provider._get_api_url()
        assert "gemini-2.0-flash" in url
        assert "generateContent" in url

    def test_api_url_handles_models_prefix(self):
        """Should handle models/ prefix in model name."""
        provider = GeminiProvider(model="models/gemini-2.0-flash", api_key="test-key")
        url = provider._get_api_url()
        # Should not have double "models/" in URL
        assert "models/models" not in url
        assert "gemini-2.0-flash" in url

    @patch('providers.gemini_provider.requests.post')
    def test_complete_with_system_instruction(self, mock_post):
        """Gemini calls should use systemInstruction for instructions."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Hello from Gemini!"}],
                        "role": "model"
                    },
                    "finishReason": "STOP"
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = GeminiProvider(model="gemini-2.0-flash", api_key="test-key")
        provider.complete("Hello", instructions="Be helpful")

        call_args = mock_post.call_args
        request_data = call_args[1]["json"]

        assert "systemInstruction" in request_data
        assert request_data["systemInstruction"]["parts"][0]["text"] == "Be helpful"

    @patch('providers.gemini_provider.requests.post')
    def test_complete_without_instructions(self, mock_post):
        """Gemini calls without instructions should not have systemInstruction."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Response"}],
                        "role": "model"
                    },
                    "finishReason": "STOP"
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = GeminiProvider(model="gemini-2.0-flash", api_key="test-key")
        provider.complete("Hello")

        call_args = mock_post.call_args
        request_data = call_args[1]["json"]

        assert "systemInstruction" not in request_data

    @patch('providers.gemini_provider.requests.post')
    def test_complete_includes_generation_config(self, mock_post):
        """Gemini calls should include generationConfig."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Response"}],
                        "role": "model"
                    },
                    "finishReason": "STOP"
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = GeminiProvider(model="gemini-2.0-flash", api_key="test-key")
        provider.complete("Hello", max_tokens=1000, temperature=0.7)

        call_args = mock_post.call_args
        request_data = call_args[1]["json"]

        assert "generationConfig" in request_data
        assert request_data["generationConfig"]["maxOutputTokens"] == 1000
        assert request_data["generationConfig"]["temperature"] == 0.7

    @patch('providers.gemini_provider.requests.post')
    def test_api_key_in_url(self, mock_post):
        """API key should be passed as query parameter."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Response"}],
                        "role": "model"
                    },
                    "finishReason": "STOP"
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = GeminiProvider(model="gemini-2.0-flash", api_key="test-api-key")
        provider.complete("Hello")

        call_args = mock_post.call_args
        url = call_args[0][0]
        assert "key=test-api-key" in url

    @patch('providers.gemini_provider.requests.post')
    def test_parse_response(self, mock_post):
        """Should parse Gemini API response."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Hello from Gemini!"}],
                        "role": "model"
                    },
                    "finishReason": "STOP"
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = GeminiProvider(model="gemini-2.0-flash", api_key="test-key")
        result, usage = provider.complete("Hello")
        assert result == "Hello from Gemini!"

    @patch('providers.gemini_provider.requests.post')
    def test_parse_response_multiple_parts(self, mock_post):
        """Should concatenate multiple text parts."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Part 1. "},
                            {"text": "Part 2."}
                        ],
                        "role": "model"
                    },
                    "finishReason": "STOP"
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = GeminiProvider(model="gemini-2.0-flash", api_key="test-key")
        result, usage = provider.complete("Hello")
        assert result == "Part 1. Part 2."

    @patch('providers.gemini_provider.requests.post')
    def test_api_error_raises_exception(self, mock_post):
        """API errors should raise exceptions."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_post.return_value = mock_response

        provider = GeminiProvider(model="gemini-2.0-flash", api_key="bad-key")
        with pytest.raises(Exception):
            provider.complete("Hello")

    @patch('providers.gemini_provider.requests.post')
    def test_empty_candidates_raises_error(self, mock_post):
        """Empty candidates array should raise ValueError."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"candidates": []}
        mock_post.return_value = mock_response

        provider = GeminiProvider(model="gemini-2.0-flash", api_key="test-key")
        with pytest.raises(ValueError) as exc_info:
            provider.complete("Hello")
        assert "No candidates" in str(exc_info.value)

    @patch('providers.gemini_provider.requests.post')
    def test_safety_block_raises_error(self, mock_post):
        """Safety blocked response should raise ValueError."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "candidates": [
                {
                    "finishReason": "SAFETY",
                    "safetyRatings": [{"category": "HARM_CATEGORY_DANGEROUS", "probability": "HIGH"}]
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = GeminiProvider(model="gemini-2.0-flash", api_key="test-key")
        with pytest.raises(ValueError) as exc_info:
            provider.complete("Hello")
        assert "safety" in str(exc_info.value).lower()

    @patch('providers.gemini_provider.requests.post')
    def test_prompt_blocked_raises_error(self, mock_post):
        """Blocked prompt should raise ValueError with reason."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "promptFeedback": {
                "blockReason": "SAFETY"
            }
        }
        mock_post.return_value = mock_response

        provider = GeminiProvider(model="gemini-2.0-flash", api_key="test-key")
        with pytest.raises(ValueError) as exc_info:
            provider.complete("Hello")
        assert "blocked" in str(exc_info.value).lower()

    @patch('providers.gemini_provider.requests.post')
    def test_call_llm_with_google(self, mock_post):
        """call_llm should work with google provider."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Gemini response"}],
                        "role": "model"
                    },
                    "finishReason": "STOP"
                }
            ]
        }
        mock_post.return_value = mock_response

        from utils import call_llm
        result = call_llm(
            model_config="google:gemini-2.0-flash",
            prompt="Hello",
            api_keys={"google": "test-key"},
        )

        assert result == "Gemini response"
