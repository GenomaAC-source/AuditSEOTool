"""Configuration dataclasses for AI providers."""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class ProviderType(Enum):
    """Supported AI provider types."""
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    TEMPLATE = "template"


@dataclass
class ProviderConfig:
    """Configuration for a single AI provider."""
    provider_type: ProviderType
    api_key: Optional[str] = None
    model: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.7
    enabled: bool = True

    # Rate limit handling
    max_retries: int = 3
    retry_delay_seconds: int = 5
    max_retry_wait_seconds: int = 60  # Will be extended to 120s for Gemini free tier

    def __post_init__(self):
        """Set default models based on provider type."""
        if self.model is None:
            defaults = {
                ProviderType.CLAUDE: "claude-sonnet-4-20250514",
                ProviderType.OPENAI: "gpt-4o",
                ProviderType.GEMINI: "gemini-2.0-flash",
                ProviderType.TEMPLATE: None,
            }
            self.model = defaults.get(self.provider_type)

    def is_available(self) -> bool:
        """Check if provider can be used."""
        if not self.enabled:
            return False
        if self.provider_type == ProviderType.TEMPLATE:
            return True
        return self.api_key is not None and len(self.api_key) > 0


@dataclass
class AIConfig:
    """Main configuration for AI system."""
    enabled: bool = True
    fallback_to_template: bool = True

    # Provider priority order
    provider_priority: List[ProviderType] = field(
        default_factory=lambda: [
            ProviderType.CLAUDE,
            ProviderType.OPENAI,
            ProviderType.GEMINI,
        ]
    )

    # Individual provider configs
    claude: ProviderConfig = field(
        default_factory=lambda: ProviderConfig(ProviderType.CLAUDE)
    )
    openai: ProviderConfig = field(
        default_factory=lambda: ProviderConfig(ProviderType.OPENAI)
    )
    gemini: ProviderConfig = field(
        default_factory=lambda: ProviderConfig(ProviderType.GEMINI)
    )
    template: ProviderConfig = field(
        default_factory=lambda: ProviderConfig(ProviderType.TEMPLATE)
    )

    # Session-level disabled providers (for quota exceeded)
    _disabled_for_session: set = field(default_factory=set)

    def get_provider_config(self, provider_type: ProviderType) -> ProviderConfig:
        """Get config for a specific provider."""
        mapping = {
            ProviderType.CLAUDE: self.claude,
            ProviderType.OPENAI: self.openai,
            ProviderType.GEMINI: self.gemini,
            ProviderType.TEMPLATE: self.template,
        }
        return mapping.get(provider_type)

    def disable_provider_for_session(self, provider_type: ProviderType):
        """Disable a provider for the current session (e.g., quota exceeded)."""
        self._disabled_for_session.add(provider_type)

    def is_provider_available(self, provider_type: ProviderType) -> bool:
        """Check if a provider is available for use."""
        if provider_type in self._disabled_for_session:
            return False
        config = self.get_provider_config(provider_type)
        return config is not None and config.is_available()

    def get_ordered_providers(self) -> List[ProviderType]:
        """Get providers in priority order, filtered by availability."""
        available = []
        for provider_type in self.provider_priority:
            if self.is_provider_available(provider_type):
                available.append(provider_type)

        # Always add template as final fallback if enabled
        if self.fallback_to_template and ProviderType.TEMPLATE not in available:
            available.append(ProviderType.TEMPLATE)

        return available

    @classmethod
    def from_env(cls) -> "AIConfig":
        """Create config from environment variables."""
        import os
        from dotenv import load_dotenv

        load_dotenv()

        config = cls()

        # Load API keys from environment
        claude_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

        if claude_key:
            config.claude.api_key = claude_key
        if openai_key:
            config.openai.api_key = openai_key
        if gemini_key:
            config.gemini.api_key = gemini_key

        return config
