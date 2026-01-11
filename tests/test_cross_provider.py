# tests/test_cross_provider.py

"""
Cross-provider integration tests for the LLM provider abstraction layer.

Tests cover:
- Consistent behavior across all providers
- Provider factory with all registered providers
- Configuration parsing for all provider formats
- Error handling consistency
- API key validation across providers
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
    BaseProvider,
    OpenAIProvider,
    XAIProvider,
    AnthropicProvider,
    GeminiProvider,
)


class TestAllProvidersRegistered:
    """Verify all expected providers are registered."""

    def test_all_four_providers_available(self):
        """All 4 providers should be registered."""
        providers = list_providers()
        assert len(providers) == 4
        assert "openai" in providers
        assert "xai" in providers
        assert "anthropic" in providers
        assert "google" in providers

    def test_provider_classes_inherit_from_base(self):
        """All provider classes should inherit from BaseProvider."""
        assert issubclass(OpenAIProvider, BaseProvider)
        assert issubclass(XAIProvider, BaseProvider)
        assert issubclass(AnthropicProvider, BaseProvider)
        assert issubclass(GeminiProvider, BaseProvider)


class TestProviderFactoryAllProviders:
    """Test get_provider factory with all providers."""

    @pytest.mark.parametrize("config,api_key_param,expected_class,expected_name", [
        ("openai:gpt-4o-mini", "openai_api_key", OpenAIProvider, "openai"),
        ("xai:grok-3-mini", "xai_api_key", XAIProvider, "xai"),
        ("anthropic:claude-sonnet-4-20250514", "anthropic_api_key", AnthropicProvider, "anthropic"),
        ("google:gemini-2.0-flash", "google_api_key", GeminiProvider, "google"),
    ])
    def test_get_provider_all_types(self, config, api_key_param, expected_class, expected_name):
        """Factory should return correct provider type for each config."""
        kwargs = {api_key_param: "test-key"}
        provider = get_provider(config, **kwargs)

        assert isinstance(provider, expected_class)
        assert provider.get_provider_name() == expected_name

    @pytest.mark.parametrize("provider_name", ["openai", "xai", "anthropic", "google"])
    def test_missing_api_key_raises_error(self, provider_name):
        """Missing API key should raise ValueError for all providers."""
        config = f"{provider_name}:test-model"
        with pytest.raises(ValueError) as exc_info:
            get_provider(config)
        assert "API key required" in str(exc_info.value)
        assert provider_name in str(exc_info.value)


class TestConfigParsingAllFormats:
    """Test configuration parsing for all provider formats."""

    @pytest.mark.parametrize("config,expected_provider,expected_model", [
        # Old format (defaults to OpenAI)
        ("gpt-4o-mini", "openai", "gpt-4o-mini"),
        ("gpt-5-mini", "openai", "gpt-5-mini"),
        # New format - all providers
        ("openai:gpt-4o", "openai", "gpt-4o"),
        ("xai:grok-3", "xai", "grok-3"),
        ("anthropic:claude-haiku-20240307", "anthropic", "claude-haiku-20240307"),
        ("google:gemini-pro", "google", "gemini-pro"),
        # Case insensitivity
        ("OpenAI:gpt-4o-mini", "openai", "gpt-4o-mini"),
        ("XAI:grok-3-mini", "xai", "grok-3-mini"),
        ("ANTHROPIC:claude-sonnet-4-20250514", "anthropic", "claude-sonnet-4-20250514"),
        ("GOOGLE:gemini-2.0-flash", "google", "gemini-2.0-flash"),
        # Model names with special characters
        ("google:models/gemini-2.0-flash", "google", "models/gemini-2.0-flash"),
        ("anthropic:claude-3-5-sonnet-20241022", "anthropic", "claude-3-5-sonnet-20241022"),
    ])
    def test_parse_all_formats(self, config, expected_provider, expected_model):
        """Configuration parser should handle all formats correctly."""
        provider, model = parse_model_config(config)
        assert provider == expected_provider
        assert model == expected_model


class TestProviderInterfaceConsistency:
    """Test that all providers implement the interface consistently."""

    @pytest.fixture
    def all_providers(self):
        """Create instances of all providers."""
        return [
            OpenAIProvider(model="gpt-4o-mini", api_key="test-key"),
            XAIProvider(model="grok-3-mini", api_key="test-key"),
            AnthropicProvider(model="claude-sonnet-4-20250514", api_key="test-key"),
            GeminiProvider(model="gemini-2.0-flash", api_key="test-key"),
        ]

    def test_all_have_complete_method(self, all_providers):
        """All providers should have complete method."""
        for provider in all_providers:
            assert hasattr(provider, 'complete')
            assert callable(provider.complete)

    def test_all_have_get_provider_name(self, all_providers):
        """All providers should have get_provider_name method."""
        for provider in all_providers:
            assert hasattr(provider, 'get_provider_name')
            name = provider.get_provider_name()
            assert isinstance(name, str)
            assert len(name) > 0

    def test_all_have_get_model_name(self, all_providers):
        """All providers should have get_model_name method."""
        for provider in all_providers:
            assert hasattr(provider, 'get_model_name')
            model = provider.get_model_name()
            assert isinstance(model, str)
            assert len(model) > 0

    def test_all_have_validate_config(self, all_providers):
        """All providers should have validate_config method."""
        for provider in all_providers:
            assert hasattr(provider, 'validate_config')
            result = provider.validate_config()
            assert result is True  # All should be valid with test data

    def test_all_have_repr(self, all_providers):
        """All providers should have useful repr."""
        for provider in all_providers:
            repr_str = repr(provider)
            assert provider.__class__.__name__ in repr_str
            assert provider.model in repr_str


class TestCrossProviderMockedCompletion:
    """Test completion behavior across all providers with mocked APIs."""

    def _mock_openai_response(self):
        return {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "OpenAI response"}]
                }
            ]
        }

    def _mock_xai_response(self):
        return {
            "choices": [{"message": {"role": "assistant", "content": "xAI response"}}]
        }

    def _mock_anthropic_response(self):
        return {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Anthropic response"}],
            "stop_reason": "end_turn"
        }

    def _mock_gemini_response(self):
        return {
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

    @patch('providers.openai_provider.requests.post')
    def test_openai_completion(self, mock_post):
        """OpenAI provider should return text from completion."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = self._mock_openai_response()
        mock_post.return_value = mock_response

        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")
        result = provider.complete("Test prompt", instructions="Be helpful")

        assert result == "OpenAI response"
        assert mock_post.called

    @patch('providers.xai_provider.requests.post')
    def test_xai_completion(self, mock_post):
        """xAI provider should return text from completion."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = self._mock_xai_response()
        mock_post.return_value = mock_response

        provider = XAIProvider(model="grok-3-mini", api_key="test-key")
        result = provider.complete("Test prompt", instructions="Be helpful")

        assert result == "xAI response"
        assert mock_post.called

    @patch('providers.anthropic_provider.requests.post')
    def test_anthropic_completion(self, mock_post):
        """Anthropic provider should return text from completion."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = self._mock_anthropic_response()
        mock_post.return_value = mock_response

        provider = AnthropicProvider(model="claude-sonnet-4-20250514", api_key="test-key")
        result = provider.complete("Test prompt", instructions="Be helpful")

        assert result == "Anthropic response"
        assert mock_post.called

    @patch('providers.gemini_provider.requests.post')
    def test_gemini_completion(self, mock_post):
        """Gemini provider should return text from completion."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = self._mock_gemini_response()
        mock_post.return_value = mock_response

        provider = GeminiProvider(model="gemini-2.0-flash", api_key="test-key")
        result = provider.complete("Test prompt", instructions="Be helpful")

        assert result == "Gemini response"
        assert mock_post.called


class TestCrossProviderErrorHandling:
    """Test error handling consistency across providers."""

    @pytest.mark.parametrize("provider_class,module_path", [
        (OpenAIProvider, 'providers.openai_provider.requests.post'),
        (XAIProvider, 'providers.xai_provider.requests.post'),
        (AnthropicProvider, 'providers.anthropic_provider.requests.post'),
        (GeminiProvider, 'providers.gemini_provider.requests.post'),
    ])
    def test_api_401_error_handling(self, provider_class, module_path):
        """All providers should handle 401 errors consistently."""
        with patch(module_path) as mock_post:
            mock_response = MagicMock()
            mock_response.ok = False
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
            mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
            mock_post.return_value = mock_response

            provider = provider_class(model="test-model", api_key="bad-key")
            with pytest.raises(Exception):
                provider.complete("Hello")

    @pytest.mark.parametrize("provider_class,module_path", [
        (OpenAIProvider, 'providers.openai_provider.requests.post'),
        (XAIProvider, 'providers.xai_provider.requests.post'),
        (AnthropicProvider, 'providers.anthropic_provider.requests.post'),
        (GeminiProvider, 'providers.gemini_provider.requests.post'),
    ])
    def test_api_429_rate_limit_handling(self, provider_class, module_path):
        """All providers should handle 429 rate limit errors."""
        with patch(module_path) as mock_post:
            mock_response = MagicMock()
            mock_response.ok = False
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            mock_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}
            mock_response.raise_for_status.side_effect = Exception("429 Too Many Requests")
            mock_post.return_value = mock_response

            provider = provider_class(model="test-model", api_key="test-key")
            with pytest.raises(Exception):
                provider.complete("Hello")


class TestCallLLMAllProviders:
    """Test call_llm utility function with all providers."""

    @patch('providers.openai_provider.requests.post')
    def test_call_llm_openai(self, mock_post):
        """call_llm should work with OpenAI."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "OK"}]}]
        }
        mock_post.return_value = mock_response

        from utils import call_llm
        result = call_llm("openai:gpt-4o-mini", "Hello", api_keys={"openai": "key"})
        assert result == "OK"

    @patch('providers.xai_provider.requests.post')
    def test_call_llm_xai(self, mock_post):
        """call_llm should work with xAI."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "OK"}}]
        }
        mock_post.return_value = mock_response

        from utils import call_llm
        result = call_llm("xai:grok-3-mini", "Hello", api_keys={"xai": "key"})
        assert result == "OK"

    @patch('providers.anthropic_provider.requests.post')
    def test_call_llm_anthropic(self, mock_post):
        """call_llm should work with Anthropic."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "OK"}]
        }
        mock_post.return_value = mock_response

        from utils import call_llm
        result = call_llm("anthropic:claude-sonnet-4-20250514", "Hello", api_keys={"anthropic": "key"})
        assert result == "OK"

    @patch('providers.gemini_provider.requests.post')
    def test_call_llm_google(self, mock_post):
        """call_llm should work with Google."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "OK"}]}}]
        }
        mock_post.return_value = mock_response

        from utils import call_llm
        result = call_llm("google:gemini-2.0-flash", "Hello", api_keys={"google": "key"})
        assert result == "OK"


class TestBackwardCompatibility:
    """Test backward compatibility with old configuration format."""

    @patch('providers.openai_provider.requests.post')
    def test_old_format_still_works(self, mock_post):
        """Old format without provider prefix should still work."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "OK"}]}]
        }
        mock_post.return_value = mock_response

        # Old format: just model name
        provider = get_provider("gpt-4o-mini", openai_api_key="test-key")
        assert isinstance(provider, OpenAIProvider)

        result = provider.complete("Hello")
        assert result == "OK"

    @patch('providers.openai_provider.requests.post')
    def test_call_responses_api_still_works(self, mock_post):
        """Deprecated call_responses_api should still work."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "OK"}]}]
        }
        mock_post.return_value = mock_response

        from utils import call_responses_api
        result = call_responses_api(
            model="gpt-4o-mini",
            prompt="Hello",
            openai_api_key="test-key"
        )
        assert result == "OK"
