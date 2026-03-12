"""API key validation for AI providers."""

from typing import Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of API key validation."""
    valid: bool
    message: str
    models_available: List[str] = None

    def __post_init__(self):
        if self.models_available is None:
            self.models_available = []


# Available models per provider
CLAUDE_MODELS = [
    ("claude-sonnet-4-20250514", "Claude Sonnet 4 (Raccomandato)"),
    ("claude-opus-4-20250514", "Claude Opus 4 (Più potente)"),
    ("claude-3-5-haiku-20241022", "Claude 3.5 Haiku (Veloce ed economico)"),
]

OPENAI_MODELS = [
    ("gpt-4o", "GPT-4o (Raccomandato)"),
    ("gpt-4o-mini", "GPT-4o Mini (Economico)"),
    ("gpt-4-turbo", "GPT-4 Turbo"),
    ("gpt-3.5-turbo", "GPT-3.5 Turbo (Economico)"),
]

GEMINI_MODELS = [
    ("gemini-2.0-flash", "Gemini 2.0 Flash (Raccomandato)"),
    ("gemini-2.5-flash", "Gemini 2.5 Flash (Nuovo)"),
    ("gemini-2.5-pro", "Gemini 2.5 Pro (Più potente)"),
    ("gemini-2.0-flash-lite", "Gemini 2.0 Flash Lite (Veloce)"),
]


def validate_claude_key(api_key: str) -> ValidationResult:
    """Validate Claude (Anthropic) API key.

    Args:
        api_key: The API key to validate

    Returns:
        ValidationResult with status and message
    """
    if not api_key or not api_key.strip():
        return ValidationResult(
            valid=False,
            message="Chiave non inserita"
        )

    api_key = api_key.strip()

    # Basic format check
    if not api_key.startswith("sk-ant-"):
        return ValidationResult(
            valid=False,
            message="Formato non valido (deve iniziare con 'sk-ant-')"
        )

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)

        # Make a minimal API call to validate
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )

        return ValidationResult(
            valid=True,
            message="Chiave valida",
            models_available=[m[0] for m in CLAUDE_MODELS]
        )

    except Exception as e:
        error_str = str(e).lower()

        if "authentication" in error_str or "api_key" in error_str or "401" in str(e):
            return ValidationResult(
                valid=False,
                message="Chiave non valida o non autorizzata"
            )
        elif "rate" in error_str or "429" in str(e):
            # Rate limited but key is valid
            return ValidationResult(
                valid=True,
                message="Chiave valida (rate limit temporaneo)",
                models_available=[m[0] for m in CLAUDE_MODELS]
            )
        elif "credit" in error_str or "billing" in error_str:
            return ValidationResult(
                valid=False,
                message="Credito esaurito o problema di fatturazione"
            )
        else:
            return ValidationResult(
                valid=False,
                message=f"Errore: {str(e)[:50]}"
            )


def validate_openai_key(api_key: str) -> ValidationResult:
    """Validate OpenAI API key.

    Args:
        api_key: The API key to validate

    Returns:
        ValidationResult with status and message
    """
    if not api_key or not api_key.strip():
        return ValidationResult(
            valid=False,
            message="Chiave non inserita"
        )

    api_key = api_key.strip()

    # Basic format check - OpenAI keys can be:
    # - sk-... (legacy)
    # - sk-proj-... (project-based, newer)
    # - sk-svcacct-... (service account)
    if not api_key.startswith("sk-"):
        return ValidationResult(
            valid=False,
            message="Formato non valido (deve iniziare con 'sk-')"
        )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        # Make a minimal API call to validate using gpt-4o-mini (cheaper)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=5,
            messages=[{"role": "user", "content": "Hi"}]
        )

        return ValidationResult(
            valid=True,
            message="Chiave valida",
            models_available=[m[0] for m in OPENAI_MODELS]
        )

    except Exception as e:
        error_str = str(e).lower()
        error_full = str(e)

        if "authentication" in error_str or "invalid_api_key" in error_str or "401" in error_full:
            return ValidationResult(
                valid=False,
                message="Chiave non valida o non autorizzata"
            )
        elif "rate" in error_str or "429" in error_full:
            return ValidationResult(
                valid=True,
                message="Chiave valida (rate limit temporaneo)",
                models_available=[m[0] for m in OPENAI_MODELS]
            )
        elif "quota" in error_str or "billing" in error_str or "insufficient_quota" in error_str:
            return ValidationResult(
                valid=False,
                message="Quota esaurita o problema di fatturazione"
            )
        elif "model" in error_str and ("not found" in error_str or "does not exist" in error_str):
            # Model not found but key is valid
            return ValidationResult(
                valid=True,
                message="Chiave valida (modello test non disponibile)",
                models_available=[m[0] for m in OPENAI_MODELS]
            )
        else:
            return ValidationResult(
                valid=False,
                message=f"Errore: {error_full[:100]}"
            )


def validate_gemini_key(api_key: str) -> ValidationResult:
    """Validate Google (Gemini) API key.

    Args:
        api_key: The API key to validate

    Returns:
        ValidationResult with status and message
    """
    if not api_key or not api_key.strip():
        return ValidationResult(
            valid=False,
            message="Chiave non inserita"
        )

    api_key = api_key.strip()

    # Gemini keys don't have a standard prefix, but they're typically 39 chars
    if len(api_key) < 30:
        return ValidationResult(
            valid=False,
            message="Formato non valido (chiave troppo corta)"
        )

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        # Try multiple models in case some are not available
        test_models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.0-flash-lite"]
        last_error = None

        for model_name in test_models:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Hi")
                # If we get here, the model worked
                break
            except Exception as e:
                last_error = e
                continue
        else:
            # All models failed
            raise last_error

        return ValidationResult(
            valid=True,
            message="Chiave valida",
            models_available=[m[0] for m in GEMINI_MODELS]
        )

    except Exception as e:
        error_str = str(e).lower()

        if "api_key" in error_str or "401" in str(e) or "invalid" in error_str:
            return ValidationResult(
                valid=False,
                message="Chiave non valida"
            )
        elif "quota" in error_str or "429" in str(e) or "resourceexhausted" in error_str or "exceeded" in error_str:
            # Rate limited or quota exceeded - key is valid but can't use right now
            return ValidationResult(
                valid=True,
                message="Chiave valida (quota esaurita - riprova tra qualche minuto)",
                models_available=[m[0] for m in GEMINI_MODELS]
            )
        elif "404" in str(e) or "not found" in error_str:
            return ValidationResult(
                valid=False,
                message="Modello non trovato - verifica la configurazione"
            )
        else:
            return ValidationResult(
                valid=False,
                message=f"Errore: {str(e)[:80]}"
            )


def get_models_for_provider(provider: str) -> List[Tuple[str, str]]:
    """Get available models for a provider.

    Args:
        provider: Provider name ('claude', 'openai', 'gemini')

    Returns:
        List of (model_id, display_name) tuples
    """
    models = {
        "claude": CLAUDE_MODELS,
        "openai": OPENAI_MODELS,
        "gemini": GEMINI_MODELS,
    }
    return models.get(provider, [])
