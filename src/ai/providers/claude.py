"""Claude (Anthropic) AI provider implementation."""

import time
from typing import Dict, Any, List, Optional

from ..config import ProviderConfig
from ..exceptions import RateLimitError, QuotaExceededError, ProviderUnavailableError
from .base import AIProvider, GenerationResult, GenerationSource


class ClaudeProvider(AIProvider):
    """AI provider using Claude API."""

    def __init__(self, config: ProviderConfig):
        """Initialize Claude provider.

        Args:
            config: Provider configuration
        """
        self.config = config
        self._client = None

    @property
    def name(self) -> str:
        return "Claude"

    @property
    def source(self) -> GenerationSource:
        return GenerationSource.CLAUDE

    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.config.api_key)
            except ImportError:
                raise ProviderUnavailableError(
                    "anthropic package not installed. Run: pip install anthropic",
                    provider=self.name
                )
        return self._client

    def is_available(self) -> bool:
        """Check if Claude is available."""
        return self.config.is_available()

    def generate_section(
        self,
        section_key: str,
        section_data: Dict[str, Any],
        site_name: str,
        site_url: str,
        feedback_examples: List[Dict] = None,
        premise_template: str = ""
    ) -> GenerationResult:
        """Generate section content using Claude."""
        from ..prompts.templates import get_section_prompt, SYSTEM_PROMPT

        start_time = time.time()

        # Build the user prompt
        context = self._build_context(section_key, section_data, site_name, site_url)
        feedback_context = self._build_feedback_context(feedback_examples or [])
        section_prompt = get_section_prompt(section_key)

        user_message = f"""
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

        try:
            client = self._get_client()

            response = client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract text from response
            raw_text = response.content[0].text

            # Parse the response
            situation, improvements = self._parse_response(raw_text)

            return GenerationResult(
                current_situation=situation,
                improvements=improvements,
                source=self.source,
                success=True,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                model=self.config.model,
                latency_ms=latency_ms,
                raw_response=raw_text
            )

        except Exception as e:
            return self._handle_error(e, start_time)

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
        if "rate" in error_str or "429" in str(error):
            retry_after = self._extract_retry_after(error)
            raise RateLimitError(
                f"Claude rate limit exceeded: {error}",
                retry_after=retry_after,
                provider=self.name
            )

        # Check for quota exceeded
        if "quota" in error_str or "credit" in error_str or "billing" in error_str:
            raise QuotaExceededError(
                f"Claude quota exceeded: {error}",
                provider=self.name
            )

        # Check for authentication issues
        if "auth" in error_str or "api_key" in error_str or "401" in str(error):
            raise ProviderUnavailableError(
                f"Claude authentication failed: {error}",
                provider=self.name
            )

        # Check for service unavailable
        if "503" in str(error) or "502" in str(error) or "overloaded" in error_str:
            raise ProviderUnavailableError(
                f"Claude service unavailable: {error}",
                provider=self.name
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
