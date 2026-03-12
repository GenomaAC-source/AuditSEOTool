"""Abstract base class for AI providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class GenerationSource(Enum):
    """Source of the generated content."""
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    TEMPLATE = "template"


@dataclass
class GenerationResult:
    """Result from AI generation."""
    current_situation: str
    improvements: str
    source: GenerationSource
    success: bool = True
    error_message: Optional[str] = None

    # Metadata
    tokens_used: Optional[int] = None
    model: Optional[str] = None
    latency_ms: Optional[float] = None

    # For debugging/logging
    raw_response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_situation": self.current_situation,
            "improvements": self.improvements,
            "source": self.source.value,
            "success": self.success,
            "error_message": self.error_message,
            "tokens_used": self.tokens_used,
            "model": self.model,
            "latency_ms": self.latency_ms,
        }


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return provider name."""
        pass

    @property
    @abstractmethod
    def source(self) -> GenerationSource:
        """Return generation source enum."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available for use."""
        pass

    @abstractmethod
    def generate_section(
        self,
        section_key: str,
        section_data: Dict[str, Any],
        site_name: str,
        site_url: str,
        feedback_examples: List[Dict] = None,
        premise_template: str = ""
    ) -> GenerationResult:
        """Generate content for a section.

        Args:
            section_key: Key identifying the section (e.g., 'alberatura', 'canonical')
            section_data: Analysis data for the section
            site_name: Name of the site being analyzed
            site_url: URL of the site
            feedback_examples: Previous feedback for few-shot learning
            premise_template: Static premise text (from NarrativeGenerator.PREMISES)

        Returns:
            GenerationResult with current_situation and improvements
        """
        pass

    def _build_context(
        self,
        section_key: str,
        section_data: Dict[str, Any],
        site_name: str,
        site_url: str
    ) -> str:
        """Build context string from section data."""
        import json

        context_parts = [
            f"Sito web: {site_name}",
            f"URL: {site_url}",
            f"Sezione: {section_key}",
            "",
            "Dati analisi:",
        ]

        def format_value(value, indent=2):
            """Format a value for display, handling nested structures."""
            prefix = "  " * indent
            if isinstance(value, dict):
                lines = []
                for k, v in value.items():
                    if isinstance(v, (dict, list)):
                        lines.append(f"{prefix}{k}:")
                        lines.append(format_value(v, indent + 1))
                    else:
                        lines.append(f"{prefix}{k}: {v}")
                return "\n".join(lines)
            elif isinstance(value, list):
                if not value:
                    return f"{prefix}(vuoto)"
                lines = []
                for i, item in enumerate(value[:10]):  # Limit to 10 items
                    if isinstance(item, dict):
                        lines.append(f"{prefix}[{i+1}]:")
                        for k, v in item.items():
                            if isinstance(v, list):
                                # For nested lists (like urls), join them
                                if v and isinstance(v[0], str):
                                    lines.append(f"{prefix}  {k}: {', '.join(str(x) for x in v[:5])}")
                                else:
                                    lines.append(f"{prefix}  {k}: {v}")
                            else:
                                lines.append(f"{prefix}  {k}: {v}")
                    else:
                        lines.append(f"{prefix}- {item}")
                if len(value) > 10:
                    lines.append(f"{prefix}... e altri {len(value) - 10} elementi")
                return "\n".join(lines)
            else:
                return f"{prefix}{value}"

        for key, value in section_data.items():
            if isinstance(value, (dict, list)):
                context_parts.append(f"  {key}:")
                context_parts.append(format_value(value, indent=2))
            else:
                context_parts.append(f"  - {key}: {value}")

        return "\n".join(context_parts)

    def _build_feedback_context(self, feedback_examples: List[Dict]) -> str:
        """Build few-shot context from feedback examples."""
        if not feedback_examples:
            return ""

        parts = [
            "",
            "Ecco esempi di feedback ricevuti su sezioni simili:",
            ""
        ]

        for i, example in enumerate(feedback_examples[:3], 1):  # Max 3 examples
            parts.append(f"Esempio {i}:")
            if example.get("original_text"):
                # Truncate long text
                original = example["original_text"][:200]
                if len(example["original_text"]) > 200:
                    original += "..."
                parts.append(f'- Testo generato: "{original}"')
            if example.get("feedback_text"):
                parts.append(f'- Feedback utente: "{example["feedback_text"]}"')
            if example.get("rating"):
                parts.append(f"- Valutazione: {example['rating']}/5")
            parts.append("")

        parts.append("Genera tenendo conto di questo feedback.")

        return "\n".join(parts)
