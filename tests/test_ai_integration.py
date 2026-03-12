"""Tests for AI multi-provider integration."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import json
import tempfile

from src.ai.config import AIConfig, ProviderConfig, ProviderType
from src.ai.exceptions import RateLimitError, QuotaExceededError, AllProvidersFailedError
from src.ai.orchestrator import AIOrchestrator
from src.ai.providers.base import GenerationResult, GenerationSource
from src.ai.providers.template import TemplateProvider
from src.ai.feedback.storage import FeedbackStorage, SectionFeedback, FeedbackEntry
from src.ai.feedback.learning import FeedbackLearner


class TestAIConfig:
    """Tests for AIConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = AIConfig()
        assert config.enabled is True
        assert config.fallback_to_template is True
        assert ProviderType.CLAUDE in config.provider_priority

    def test_provider_availability(self):
        """Test provider availability check."""
        config = AIConfig()
        config.claude.api_key = "test-key"

        assert config.is_provider_available(ProviderType.CLAUDE) is True
        assert config.is_provider_available(ProviderType.OPENAI) is False

    def test_disable_provider_for_session(self):
        """Test disabling provider for session."""
        config = AIConfig()
        config.claude.api_key = "test-key"

        assert config.is_provider_available(ProviderType.CLAUDE) is True

        config.disable_provider_for_session(ProviderType.CLAUDE)

        assert config.is_provider_available(ProviderType.CLAUDE) is False

    def test_ordered_providers(self):
        """Test getting providers in order."""
        config = AIConfig()
        config.claude.api_key = "claude-key"
        config.gemini.api_key = "gemini-key"
        # OpenAI not configured

        providers = config.get_ordered_providers()

        # Should have Claude, Gemini, and Template (fallback)
        assert ProviderType.CLAUDE in providers
        assert ProviderType.GEMINI in providers
        assert ProviderType.TEMPLATE in providers
        assert ProviderType.OPENAI not in providers


class TestTemplateProvider:
    """Tests for TemplateProvider."""

    def test_always_available(self):
        """Test template provider is always available."""
        config = ProviderConfig(ProviderType.TEMPLATE)
        provider = TemplateProvider(config, "Test Site", "https://test.com")

        assert provider.is_available() is True

    def test_generate_alberatura(self):
        """Test generating alberatura section."""
        config = ProviderConfig(ProviderType.TEMPLATE)
        provider = TemplateProvider(config, "Test Site", "https://test.com")

        data = {
            "total_pages": 100,
            "depth_distribution": {"1": 10, "2": 50, "3": 40},
            "deep_pages_count": 5,
            "orphan_pages_count": 2
        }

        result = provider.generate_section(
            section_key="alberatura",
            section_data=data,
            site_name="Test Site",
            site_url="https://test.com"
        )

        assert result.success is True
        assert result.source == GenerationSource.TEMPLATE
        assert len(result.current_situation) > 0


class TestFeedbackStorage:
    """Tests for FeedbackStorage."""

    def test_add_and_retrieve_feedback(self):
        """Test adding and retrieving feedback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = FeedbackStorage(Path(tmpdir))

            feedback = SectionFeedback(
                section_type="alberatura",
                generated_text="Test generated text",
                user_feedback="Good job!",
                rating=4
            )

            storage.add_section_feedback(
                audit_id="test-audit-1",
                site_url="https://test.com",
                section_key="alberatura",
                feedback=feedback
            )

            retrieved = storage.get_feedback_for_section("alberatura", limit=10)

            assert len(retrieved) == 1
            assert retrieved[0].user_feedback == "Good job!"
            assert retrieved[0].rating == 4

    def test_get_high_rated_feedback(self):
        """Test getting high-rated feedback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = FeedbackStorage(Path(tmpdir))

            # Add low-rated feedback
            storage.add_section_feedback(
                audit_id="test-1",
                site_url="https://test.com",
                section_key="title",
                feedback=SectionFeedback(
                    section_type="title",
                    generated_text="Low rated",
                    user_feedback="Not good",
                    rating=2
                )
            )

            # Add high-rated feedback
            storage.add_section_feedback(
                audit_id="test-2",
                site_url="https://test.com",
                section_key="title",
                feedback=SectionFeedback(
                    section_type="title",
                    generated_text="High rated",
                    user_feedback="Excellent!",
                    rating=5
                )
            )

            high_rated = storage.get_high_rated_feedback("title", min_rating=4)

            assert len(high_rated) == 1
            assert high_rated[0].rating == 5


class TestFeedbackLearner:
    """Tests for FeedbackLearner."""

    def test_get_examples_priority(self):
        """Test examples are returned in priority order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = FeedbackStorage(Path(tmpdir))

            # Add corrected feedback (highest priority)
            storage.add_section_feedback(
                audit_id="test-1",
                site_url="https://test.com",
                section_key="description",
                feedback=SectionFeedback(
                    section_type="description",
                    generated_text="Original text",
                    user_feedback="Fixed version",
                    corrected_text="Better version of the text",
                    rating=3
                )
            )

            # Add high-rated feedback
            storage.add_section_feedback(
                audit_id="test-2",
                site_url="https://test.com",
                section_key="description",
                feedback=SectionFeedback(
                    section_type="description",
                    generated_text="Good text",
                    user_feedback="Great!",
                    rating=5
                )
            )

            learner = FeedbackLearner(storage)
            examples = learner.get_examples_for_section("description", max_examples=2)

            # Corrected should come first
            assert len(examples) == 2
            assert examples[0]["type"] == "corrected"
            assert examples[1]["type"] == "high_rated"


class TestAIOrchestrator:
    """Tests for AIOrchestrator."""

    def test_fallback_to_template(self):
        """Test fallback to template when no AI providers configured."""
        config = AIConfig()
        config.enabled = True
        # No API keys configured

        orchestrator = AIOrchestrator(
            config=config,
            site_name="Test Site",
            site_url="https://test.com"
        )

        data = {"total_pages": 50}

        result = orchestrator.generate_section_safe("alberatura", data)

        assert result.success is True
        assert result.source == GenerationSource.TEMPLATE

    @patch('src.ai.providers.claude.ClaudeProvider.generate_section')
    def test_uses_configured_provider(self, mock_generate):
        """Test using configured provider."""
        mock_generate.return_value = GenerationResult(
            current_situation="AI generated situation",
            improvements="AI generated improvements",
            source=GenerationSource.CLAUDE,
            success=True
        )

        config = AIConfig()
        config.claude.api_key = "test-key"

        orchestrator = AIOrchestrator(
            config=config,
            site_name="Test Site",
            site_url="https://test.com"
        )

        data = {"total_pages": 50}

        result = orchestrator.generate_section_safe("alberatura", data)

        assert result.success is True
        assert result.source == GenerationSource.CLAUDE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
