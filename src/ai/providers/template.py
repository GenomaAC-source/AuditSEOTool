"""Template provider - fallback using existing NarrativeGenerator."""

import time
from typing import Dict, Any, List

from ..config import ProviderConfig
from .base import AIProvider, GenerationResult, GenerationSource


class TemplateProvider(AIProvider):
    """Fallback provider using template-based NarrativeGenerator."""

    def __init__(self, config: ProviderConfig, site_name: str, site_url: str):
        """Initialize template provider.

        Args:
            config: Provider configuration
            site_name: Name of the site being analyzed
            site_url: URL of the site
        """
        self.config = config
        self.site_name = site_name
        self.site_url = site_url
        self._generator = None

    @property
    def name(self) -> str:
        return "Template"

    @property
    def source(self) -> GenerationSource:
        return GenerationSource.TEMPLATE

    def _get_generator(self):
        """Lazy initialization of NarrativeGenerator."""
        if self._generator is None:
            from ...reporters.narrative import NarrativeGenerator
            self._generator = NarrativeGenerator(self.site_name, self.site_url)
        return self._generator

    def is_available(self) -> bool:
        """Template provider is always available."""
        return True

    def generate_section(
        self,
        section_key: str,
        section_data: Dict[str, Any],
        site_name: str,
        site_url: str,
        feedback_examples: List[Dict] = None,
        premise_template: str = ""
    ) -> GenerationResult:
        """Generate section content using templates."""
        start_time = time.time()

        generator = self._get_generator()

        # Map section keys to generator methods
        section_generators = {
            "alberatura": lambda: generator.generate_alberatura(section_data),
            "canonical": lambda: generator.generate_canonical(
                section_data,
                section_data.get("duplicates_data", {})
            ),
            "hreflang": lambda: generator.generate_hreflang(section_data),
            "title": lambda: generator.generate_title(section_data),
            "description": lambda: generator.generate_description(section_data),
            "headings": lambda: generator.generate_headings(section_data),
            "images": lambda: generator.generate_images(section_data),
            "linking": lambda: generator.generate_linking(section_data),
            "structured_data": lambda: generator.generate_structured_data(section_data),
            "performance": lambda: generator.generate_performance(section_data),
        }

        try:
            gen_func = section_generators.get(section_key)

            if gen_func:
                section = gen_func()
                latency_ms = (time.time() - start_time) * 1000

                return GenerationResult(
                    current_situation=section.current_situation,
                    improvements=section.improvements,
                    source=self.source,
                    success=True,
                    model="template",
                    latency_ms=latency_ms
                )
            else:
                # Unknown section - return generic content
                return GenerationResult(
                    current_situation="Sezione analizzata.",
                    improvements="Non sono necessari miglioramenti significativi.",
                    source=self.source,
                    success=True,
                    model="template",
                    latency_ms=(time.time() - start_time) * 1000
                )

        except Exception as e:
            return GenerationResult(
                current_situation="Errore nella generazione del contenuto.",
                improvements="Verificare i dati di input.",
                source=self.source,
                success=False,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
