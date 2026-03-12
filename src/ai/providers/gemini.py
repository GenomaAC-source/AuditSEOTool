"""Google Gemini AI provider implementation."""

import time
import re
import logging
from typing import Dict, Any, List, Optional

from ..config import ProviderConfig
from ..exceptions import RateLimitError, QuotaExceededError, ProviderUnavailableError
from .base import AIProvider, GenerationResult, GenerationSource

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    """AI provider using Google Gemini API with rate limiting support."""

    # Rate limiting settings for free tier
    MIN_REQUEST_INTERVAL = 4.0  # Minimum seconds between requests (15 req/min = 4s)
    MAX_RETRIES_ON_RATE_LIMIT = 5  # Max retries when rate limited
    BASE_RETRY_DELAY = 10  # Base delay in seconds for retry

    def __init__(self, config: ProviderConfig):
        """Initialize Gemini provider.

        Args:
            config: Provider configuration
        """
        self.config = config
        self._client = None
        self._last_request_time = 0  # Track last request for rate limiting

    @property
    def name(self) -> str:
        return "Gemini"

    @property
    def source(self) -> GenerationSource:
        return GenerationSource.GEMINI

    def _get_client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.config.api_key)
                self._client = genai.GenerativeModel(self.config.model)
            except ImportError:
                raise ProviderUnavailableError(
                    "google-generativeai package not installed. Run: pip install google-generativeai",
                    provider=self.name
                )
        return self._client

    def is_available(self) -> bool:
        """Check if Gemini is available."""
        return self.config.is_available()

    def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            wait_time = self.MIN_REQUEST_INTERVAL - elapsed
            logger.info(f"Gemini rate limiting: waiting {wait_time:.1f}s")
            time.sleep(wait_time)
        self._last_request_time = time.time()

    def _extract_retry_delay_from_error(self, error: Exception) -> int:
        """Extract retry delay from error message if available."""
        error_str = str(error)
        # Look for "retry in X seconds" pattern
        match = re.search(r'retry[_ ]?in[_ ]?(\d+)', error_str.lower())
        if match:
            return int(match.group(1))
        # Look for retry_delay { seconds: X }
        match = re.search(r'seconds:\s*(\d+)', error_str)
        if match:
            return int(match.group(1))
        return self.BASE_RETRY_DELAY

    def generate_section(
        self,
        section_key: str,
        section_data: Dict[str, Any],
        site_name: str,
        site_url: str,
        feedback_examples: List[Dict] = None,
        premise_template: str = ""
    ) -> GenerationResult:
        """Generate section content using Gemini with rate limiting."""
        from ..prompts.templates import get_section_prompt, SYSTEM_PROMPT

        start_time = time.time()

        # Build the user prompt
        context = self._build_context(section_key, section_data, site_name, site_url)
        feedback_context = self._build_feedback_context(feedback_examples or [])
        section_prompt = get_section_prompt(section_key)

        # Gemini uses a combined prompt (system + user)
        full_prompt = f"""
{SYSTEM_PROMPT}

---

{context}

{feedback_context}

{section_prompt}

La premessa (già scritta) è:
"{premise_template}"

Genera SOLO la "Situazione attuale" e "Come migliorare".
Rispondi in italiano, con tono professionale da consulente SEO.

FORMATO RISPOSTA:
SITUAZIONE_ATTUALE:
[il tuo testo qui]

MIGLIORAMENTI:
[il tuo testo qui]
"""

        # Retry loop with rate limiting
        last_error = None
        for attempt in range(self.MAX_RETRIES_ON_RATE_LIMIT):
            try:
                # Wait to respect rate limits
                self._wait_for_rate_limit()

                client = self._get_client()

                # Configure generation parameters
                generation_config = {
                    "temperature": self.config.temperature,
                    "max_output_tokens": self.config.max_tokens,
                }

                logger.info(f"Gemini request attempt {attempt + 1}/{self.MAX_RETRIES_ON_RATE_LIMIT} for {section_key}")

                response = client.generate_content(
                    full_prompt,
                    generation_config=generation_config
                )

                latency_ms = (time.time() - start_time) * 1000

                # Extract text from response
                raw_text = response.text

                # Parse the response
                situation, improvements = self._parse_response(raw_text)

                # Gemini doesn't always provide token counts in the same way
                tokens_used = None
                if hasattr(response, 'usage_metadata'):
                    tokens_used = getattr(response.usage_metadata, 'total_token_count', None)

                logger.info(f"Gemini generation successful for {section_key}")

                return GenerationResult(
                    current_situation=situation,
                    improvements=improvements,
                    source=self.source,
                    success=True,
                    tokens_used=tokens_used,
                    model=self.config.model,
                    latency_ms=latency_ms,
                    raw_response=raw_text
                )

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check if it's a rate limit error
                if "429" in str(e) or "quota" in error_str or "resourceexhausted" in error_str or "exceeded" in error_str:
                    retry_delay = self._extract_retry_delay_from_error(e)
                    # Cap the retry delay to avoid waiting too long
                    retry_delay = min(retry_delay, 60)

                    if attempt < self.MAX_RETRIES_ON_RATE_LIMIT - 1:
                        logger.warning(f"Gemini rate limited, waiting {retry_delay}s before retry (attempt {attempt + 1})")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.warning(f"Gemini rate limited, max retries reached")
                        # Don't raise, let it fall through to return error result
                else:
                    # Non-rate-limit error, don't retry
                    break

        # All retries failed or non-retriable error
        return self._handle_error(last_error, start_time)

    def _parse_response(self, raw_text: str) -> tuple:
        """Parse the AI response into situation and improvements."""
        situation = ""
        improvements = ""

        # Try to parse structured response
        if "SITUAZIONE_ATTUALE:" in raw_text and "MIGLIORAMENTI:" in raw_text:
            parts = raw_text.split("MIGLIORAMENTI:")
            situation_part = parts[0].replace("SITUAZIONE_ATTUALE:", "").strip()
            improvements_part = parts[1].strip() if len(parts) > 1 else ""

            situation = situation_part
            improvements = improvements_part
        else:
            # Fallback: split in half if no markers found
            lines = raw_text.strip().split("\n")
            mid = len(lines) // 2
            situation = "\n".join(lines[:mid]).strip()
            improvements = "\n".join(lines[mid:]).strip()

        return situation, improvements

    def _handle_error(self, error: Exception, start_time: float) -> GenerationResult:
        """Handle API errors and convert to appropriate exceptions."""
        error_str = str(error).lower()
        latency_ms = (time.time() - start_time) * 1000

        # Check for rate limit
        if "rate" in error_str or "429" in str(error) or "quota" in error_str:
            # Gemini often returns quota errors as rate limits
            if "quota" in error_str:
                raise QuotaExceededError(
                    f"Gemini quota exceeded: {error}",
                    provider=self.name
                )

            retry_after = self._extract_retry_after(error)
            raise RateLimitError(
                f"Gemini rate limit exceeded: {error}",
                retry_after=retry_after,
                provider=self.name
            )

        # Check for authentication issues
        if "api_key" in error_str or "401" in str(error) or "invalid" in error_str:
            raise ProviderUnavailableError(
                f"Gemini authentication failed: {error}",
                provider=self.name
            )

        # Check for service unavailable
        if "503" in str(error) or "502" in str(error) or "unavailable" in error_str:
            raise ProviderUnavailableError(
                f"Gemini service unavailable: {error}",
                provider=self.name
            )

        # Check for blocked content
        if "blocked" in error_str or "safety" in error_str:
            return GenerationResult(
                current_situation="Contenuto non generato per policy di sicurezza.",
                improvements="Verificare i dati di input.",
                source=self.source,
                success=False,
                error_message=f"Content blocked: {error}",
                latency_ms=latency_ms
            )

        # Return failed result for other errors
        return GenerationResult(
            current_situation="",
            improvements="",
            source=self.source,
            success=False,
            error_message=str(error),
            latency_ms=latency_ms
        )

    def _extract_retry_after(self, error: Exception) -> Optional[int]:
        """Extract retry-after value from error if available."""
        error_str = str(error)

        # Try to find a number in the error message
        import re
        match = re.search(r'(\d+)\s*second', error_str)
        if match:
            return int(match.group(1))

        # Default retry after
        return 30
