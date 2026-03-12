"""AI Orchestrator - manages provider fallback chain."""

import time
import logging
from typing import Dict, Any, List, Optional

from .config import AIConfig, ProviderConfig, ProviderType
from .exceptions import (
    RateLimitError,
    QuotaExceededError,
    ProviderUnavailableError,
    AllProvidersFailedError,
)
from .providers.base import AIProvider, GenerationResult, GenerationSource
from .providers.claude import ClaudeProvider
from .providers.openai import OpenAIProvider
from .providers.gemini import GeminiProvider
from .providers.template import TemplateProvider

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """Manages AI providers with automatic fallback."""

    def __init__(
        self,
        config: AIConfig,
        site_name: str,
        site_url: str,
        feedback_storage=None
    ):
        """Initialize orchestrator.

        Args:
            config: AI configuration
            site_name: Name of the site being analyzed
            site_url: URL of the site
            feedback_storage: Optional FeedbackStorage instance for few-shot learning
        """
        self.config = config
        self.site_name = site_name
        self.site_url = site_url
        self.feedback_storage = feedback_storage

        # Initialize providers lazily
        self._providers: Dict[ProviderType, AIProvider] = {}

        # Track errors per provider for this session
        self._errors: Dict[str, List[str]] = {}

        # Track AI failures with details for user notification
        self._ai_failures: List[Dict[str, Any]] = []

        # Track generation stats
        self._stats = {
            "total_generations": 0,
            "by_provider": {},
            "fallbacks_used": 0,
            "template_fallbacks": 0,
            "ai_success": 0,
            "ai_failed": 0,
        }

    def _get_provider(self, provider_type: ProviderType) -> AIProvider:
        """Get or create a provider instance."""
        if provider_type not in self._providers:
            config = self.config.get_provider_config(provider_type)

            if provider_type == ProviderType.CLAUDE:
                self._providers[provider_type] = ClaudeProvider(config)
            elif provider_type == ProviderType.OPENAI:
                self._providers[provider_type] = OpenAIProvider(config)
            elif provider_type == ProviderType.GEMINI:
                self._providers[provider_type] = GeminiProvider(config)
            elif provider_type == ProviderType.TEMPLATE:
                self._providers[provider_type] = TemplateProvider(
                    config, self.site_name, self.site_url
                )

        return self._providers.get(provider_type)

    def _get_feedback_examples(self, section_key: str) -> List[Dict]:
        """Get relevant feedback examples for few-shot learning."""
        if self.feedback_storage is None:
            return []

        try:
            from .feedback.learning import FeedbackLearner
            learner = FeedbackLearner(self.feedback_storage)
            return learner.get_examples_for_section(section_key, max_examples=3)
        except Exception as e:
            logger.warning(f"Failed to load feedback examples: {e}")
            return []

    def _get_premise(self, section_key: str) -> str:
        """Get premise template for a section."""
        from ..reporters.narrative import NarrativeGenerator
        return NarrativeGenerator.PREMISES.get(section_key, "")

    def generate_section(
        self,
        section_key: str,
        section_data: Dict[str, Any]
    ) -> GenerationResult:
        """Generate content for a section with automatic fallback.

        Tries providers in priority order:
        1. Claude → 2. OpenAI → 3. Gemini → 4. Template (fallback)

        Args:
            section_key: Key identifying the section (e.g., 'alberatura')
            section_data: Analysis data for the section

        Returns:
            GenerationResult from the first successful provider
        """
        if not self.config.enabled:
            # AI disabled - use template directly
            return self._generate_with_template(section_key, section_data)

        # Get feedback examples for few-shot learning
        feedback_examples = self._get_feedback_examples(section_key)
        premise_template = self._get_premise(section_key)

        # Get ordered providers
        providers = self.config.get_ordered_providers()
        errors = {}

        for provider_type in providers:
            provider = self._get_provider(provider_type)

            if provider is None or not provider.is_available():
                continue

            try:
                logger.info(f"Trying provider: {provider.name} for section: {section_key}")

                result = provider.generate_section(
                    section_key=section_key,
                    section_data=section_data,
                    site_name=self.site_name,
                    site_url=self.site_url,
                    feedback_examples=feedback_examples,
                    premise_template=premise_template
                )

                if result.success:
                    # Track stats
                    self._stats["total_generations"] += 1
                    provider_name = provider.name
                    self._stats["by_provider"][provider_name] = \
                        self._stats["by_provider"].get(provider_name, 0) + 1

                    if provider_type == ProviderType.TEMPLATE:
                        self._stats["template_fallbacks"] += 1
                    elif provider_type != providers[0]:
                        self._stats["fallbacks_used"] += 1

                    logger.info(f"Generation successful with {provider.name}")
                    return result

                # Non-success result - continue to next provider
                errors[provider.name] = result.error_message or "Unknown error"

            except RateLimitError as e:
                logger.warning(f"Rate limit on {provider.name}: {e}")
                errors[provider.name] = str(e)

                # For Gemini, be more patient with rate limits
                max_wait = self.config.get_provider_config(provider_type).max_retry_wait_seconds
                if provider_type == ProviderType.GEMINI:
                    max_wait = max(max_wait, 120)  # At least 2 minutes for Gemini free tier

                # Check if we should wait and retry
                if e.should_retry_same_provider(max_wait):
                    wait_time = min(e.retry_after or 30, max_wait)
                    logger.info(f"Waiting {wait_time}s before retrying {provider.name}")
                    time.sleep(wait_time)

                    # Retry same provider
                    try:
                        result = provider.generate_section(
                            section_key=section_key,
                            section_data=section_data,
                            site_name=self.site_name,
                            site_url=self.site_url,
                            feedback_examples=feedback_examples,
                            premise_template=premise_template
                        )
                        if result.success:
                            return result
                    except Exception:
                        pass

                # Continue to next provider

            except QuotaExceededError as e:
                logger.warning(f"Quota exceeded on {provider.name}: {e}")
                errors[provider.name] = str(e)

                # Disable provider for session
                self.config.disable_provider_for_session(provider_type)

            except ProviderUnavailableError as e:
                logger.warning(f"Provider unavailable {provider.name}: {e}")
                errors[provider.name] = str(e)

            except Exception as e:
                logger.error(f"Unexpected error with {provider.name}: {e}")
                errors[provider.name] = str(e)

        # All providers failed
        self._errors[section_key] = list(errors.values())

        # Use template as final fallback
        if self.config.fallback_to_template:
            result = self._generate_with_template(section_key, section_data)
            self._stats["template_fallbacks"] += 1

            # Return with warning about AI failure
            raise AllProvidersFailedError(
                "All AI providers failed, using template fallback",
                errors=errors,
                template_used=True
            )

        raise AllProvidersFailedError(
            "All AI providers failed",
            errors=errors,
            template_used=False
        )

    def _generate_with_template(
        self,
        section_key: str,
        section_data: Dict[str, Any]
    ) -> GenerationResult:
        """Generate using template provider."""
        template_provider = self._get_provider(ProviderType.TEMPLATE)
        return template_provider.generate_section(
            section_key=section_key,
            section_data=section_data,
            site_name=self.site_name,
            site_url=self.site_url
        )

    def generate_section_safe(
        self,
        section_key: str,
        section_data: Dict[str, Any]
    ) -> GenerationResult:
        """Generate section with guaranteed result (uses template on any failure).

        This method never raises exceptions - it always returns a result,
        falling back to template generation if needed.

        Args:
            section_key: Key identifying the section
            section_data: Analysis data for the section

        Returns:
            GenerationResult (always successful, possibly from template)
        """
        try:
            result = self.generate_section(section_key, section_data)
            if result.source != GenerationSource.TEMPLATE:
                self._stats["ai_success"] += 1
            return result
        except AllProvidersFailedError as e:
            # Track the AI failure for user notification
            self._stats["ai_failed"] += 1
            self._ai_failures.append({
                "section": section_key,
                "reason": str(e),
                "errors": e.errors if hasattr(e, 'errors') else {},
                "used_template": True
            })
            logger.warning(f"AI generation failed for {section_key}, using template: {e}")
            return self._generate_with_template(section_key, section_data)
        except Exception as e:
            # Track unexpected failure
            self._stats["ai_failed"] += 1
            self._ai_failures.append({
                "section": section_key,
                "reason": f"Errore imprevisto: {str(e)}",
                "errors": {},
                "used_template": True
            })
            logger.error(f"Unexpected error in generation for {section_key}: {e}")
            return self._generate_with_template(section_key, section_data)

    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return self._stats.copy()

    def get_errors(self) -> Dict[str, List[str]]:
        """Get errors encountered during generation."""
        return self._errors.copy()

    def get_ai_failures(self) -> List[Dict[str, Any]]:
        """Get detailed list of AI failures for user notification.

        Returns:
            List of dicts with section, reason, errors, and whether template was used
        """
        return self._ai_failures.copy()

    def had_ai_failures(self) -> bool:
        """Check if any AI generation failed during this session."""
        return len(self._ai_failures) > 0

    def get_ai_status_summary(self) -> Dict[str, Any]:
        """Get a summary of AI usage status for user notification.

        Returns:
            Dict with ai_used, ai_available, success_count, failure_count, failure_details
        """
        ai_available = self.config.enabled and any(
            self._get_provider(pt) is not None and self._get_provider(pt).is_available()
            for pt in [ProviderType.CLAUDE, ProviderType.OPENAI, ProviderType.GEMINI]
        )

        return {
            "ai_enabled": self.config.enabled,
            "ai_available": ai_available,
            "success_count": self._stats.get("ai_success", 0),
            "failure_count": self._stats.get("ai_failed", 0),
            "template_fallbacks": self._stats.get("template_fallbacks", 0),
            "failures": self._ai_failures,
            "providers_tried": list(self._stats.get("by_provider", {}).keys()),
        }
