"""Page Classifier - AI-based classification of pages as informational/transactional/navigational."""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class PageType(Enum):
    """Page intent classification."""
    TRANSACTIONAL = "transactional"  # Product, service, checkout, pricing pages
    INFORMATIONAL = "informational"  # Blog, guide, how-to, FAQ pages
    NAVIGATIONAL = "navigational"    # Category, hub, sitemap, index pages
    UNKNOWN = "unknown"


@dataclass
class PageClassification:
    """Classification result for a single page."""
    url: str
    page_type: PageType
    confidence: float  # 0.0 to 1.0
    signals: List[str] = field(default_factory=list)  # Why this classification
    title: str = ""
    h1: str = ""


@dataclass
class ClassificationReport:
    """Complete classification report for a site."""
    total_pages: int = 0
    classified_pages: int = 0

    # Counts by type
    transactional_count: int = 0
    informational_count: int = 0
    navigational_count: int = 0
    unknown_count: int = 0

    # Page lists by type
    transactional_pages: List[PageClassification] = field(default_factory=list)
    informational_pages: List[PageClassification] = field(default_factory=list)
    navigational_pages: List[PageClassification] = field(default_factory=list)
    unknown_pages: List[PageClassification] = field(default_factory=list)

    # Classification method used
    method: str = "ai"  # "ai", "heuristic", "hybrid"

    def get_pages_by_type(self, page_type: PageType) -> List[PageClassification]:
        """Get all pages of a specific type."""
        if page_type == PageType.TRANSACTIONAL:
            return self.transactional_pages
        elif page_type == PageType.INFORMATIONAL:
            return self.informational_pages
        elif page_type == PageType.NAVIGATIONAL:
            return self.navigational_pages
        return self.unknown_pages

    def get_url_type_map(self) -> Dict[str, PageType]:
        """Get mapping of URL to page type."""
        result = {}
        for page in self.transactional_pages:
            result[page.url] = PageType.TRANSACTIONAL
        for page in self.informational_pages:
            result[page.url] = PageType.INFORMATIONAL
        for page in self.navigational_pages:
            result[page.url] = PageType.NAVIGATIONAL
        for page in self.unknown_pages:
            result[page.url] = PageType.UNKNOWN
        return result


class PageClassifier:
    """Classifies pages using AI or heuristics."""

    # URL patterns to EXCLUDE from analysis (irrelevant for SEO)
    EXCLUDE_PATTERNS = [
        r'/profile/', r'/profilo/', r'/user/', r'/utente/',
        r'/account/', r'/login/', r'/logout/', r'/register/',
        r'/signin/', r'/signup/', r'/password/', r'/reset/',
        r'/admin/', r'/wp-admin/', r'/dashboard/',
        r'/cart/', r'/carrello/', r'/checkout/', r'/payment/',
        r'/thank-you/', r'/grazie/', r'/confirmation/',
        r'/search/', r'/cerca/', r'/risultati/',
        r'/privacy/', r'/cookie/', r'/terms/', r'/legal/',
        r'/404/', r'/error/',
        r'\?', r'#',  # URLs with query strings or fragments
    ]

    # URL patterns for heuristic classification
    TRANSACTIONAL_PATTERNS = [
        r'/prodott[oi]/', r'/product[s]?/', r'/shop/', r'/negozio/',
        r'/acquist[ao]/', r'/buy/', r'/order/',
        r'/prezz[oi]/', r'/pric/',
        r'/serviz[io]/', r'/service[s]?/', r'/preventivo/',
        r'/contatt[oi]/', r'/contact/', r'/richiedi/',
        r'/prenota/', r'/book/', r'/reserve/',
        r'/collezione/', r'/collection/',
        # E-commerce specific
        r'/store/', r'/catalog/', r'/catalogo/',
    ]

    INFORMATIONAL_PATTERNS = [
        r'/blog/', r'/news/', r'/notizie/', r'/articol[oi]/',
        r'/guid[ae]/', r'/guide/', r'/come-/', r'/how-to/',
        r'/tutorial/', r'/faq/', r'/domande-frequenti/',
        r'/risorsa/', r'/resource/', r'/learn/', r'/impara/',
        r'/consig/', r'/tip[s]?/', r'/what-is/', r'/cos-e/',
        r'/post/', r'/magazine/', r'/journal/',
        r'/storia/', r'/about/', r'/chi-siamo/',
    ]

    NAVIGATIONAL_PATTERNS = [
        r'/categori[ae]/', r'/category/', r'/tag/',
        r'/archiv/', r'/author/', r'/autore/',
        r'^/$',  # Homepage
        r'/index', r'/sitemap/', r'/mappa-sito/',
    ]

    # Content signals
    TRANSACTIONAL_SIGNALS = [
        'prezzo', 'price', 'euro', 'acquista', 'buy now', 'add to cart',
        'aggiungi al carrello', 'ordina', 'order', 'disponibile',
        'available', 'spedizione', 'shipping', 'sconto', 'discount',
        'offerta', 'offer', 'promozione', 'sale',
    ]

    INFORMATIONAL_SIGNALS = [
        'guida', 'guide', 'come fare', 'how to', 'tutorial',
        'scopri', 'learn', 'consigli', 'tips', 'cosa e',
        'what is', 'perche', 'why', 'vantaggi', 'benefits',
    ]

    def __init__(self, db, ai_config=None):
        """Initialize classifier.

        Args:
            db: CrawlDatabase instance
            ai_config: Optional AIConfig for AI-based classification
        """
        self.db = db
        self.ai_config = ai_config
        self.report = ClassificationReport()
        self._classifications: Dict[str, PageClassification] = {}
        self._excluded_urls: List[str] = []

    def _should_exclude(self, url: str) -> bool:
        """Check if URL should be excluded from strategic analysis."""
        url_lower = url.lower()
        for pattern in self.EXCLUDE_PATTERNS:
            if re.search(pattern, url_lower):
                return True
        return False

    def classify_all(self, use_ai: bool = True) -> ClassificationReport:
        """Classify all pages in the database.

        Args:
            use_ai: If True and AI config available, use AI classification

        Returns:
            ClassificationReport with all classifications
        """
        pages_data = []

        for page in self.db.get_all_pages():
            if page.status_code != 200:
                continue

            # Filter out irrelevant URLs
            if self._should_exclude(page.url):
                self._excluded_urls.append(page.url)
                continue

            pages_data.append({
                'url': page.url,
                'title': page.title or '',
                'h1': page.h1 or '',
                'text_snippet': (page.text_content or '')[:500],
                'has_schema_product': self._has_product_schema(page),
            })

        self.report.total_pages = len(pages_data)

        if use_ai and self.ai_config and self.ai_config.enabled:
            try:
                self._classify_with_ai(pages_data)
                self.report.method = "ai"
            except Exception as e:
                logger.warning(f"AI classification failed, falling back to heuristic: {e}")
                self._classify_with_heuristics(pages_data)
                self.report.method = "heuristic"
        else:
            self._classify_with_heuristics(pages_data)
            self.report.method = "heuristic"

        return self.report

    def _has_product_schema(self, page) -> bool:
        """Check if page has Product schema."""
        if not page.structured_data_json:
            return False
        try:
            schemas = json.loads(page.structured_data_json)
            for schema in schemas:
                if schema.get('@type') == 'Product':
                    return True
        except:
            pass
        return False

    def _classify_with_ai(self, pages_data: List[Dict]):
        """Classify pages using AI in batches."""
        from ..ai.config import ProviderType
        from ..ai.orchestrator import AIOrchestrator

        # Process in batches of 10 pages
        BATCH_SIZE = 10

        orchestrator = AIOrchestrator(
            config=self.ai_config,
            site_name="",
            site_url=""
        )

        for i in range(0, len(pages_data), BATCH_SIZE):
            batch = pages_data[i:i + BATCH_SIZE]

            try:
                classifications = self._classify_batch_ai(orchestrator, batch)
                for classification in classifications:
                    self._add_classification(classification)
            except Exception as e:
                logger.warning(f"Batch AI classification failed: {e}")
                # Fallback to heuristic for this batch
                for page_data in batch:
                    classification = self._classify_single_heuristic(page_data)
                    self._add_classification(classification)

    def _classify_batch_ai(self, orchestrator, batch: List[Dict]) -> List[PageClassification]:
        """Classify a batch of pages using AI."""
        # Build prompt for batch classification
        pages_text = []
        for idx, page in enumerate(batch):
            pages_text.append(f"""
Pagina {idx + 1}:
- URL: {page['url']}
- Title: {page['title']}
- H1: {page['h1']}
- Schema Product: {'Si' if page.get('has_schema_product') else 'No'}
- Testo: {page['text_snippet'][:200]}...
""")

        prompt = f"""Classifica le seguenti pagine web in base al loro intento principale.

Categorie:
- TRANSACTIONAL: Pagine di prodotto, servizio, checkout, prezzi, contatti commerciali
- INFORMATIONAL: Blog, guide, how-to, FAQ, articoli educativi
- NAVIGATIONAL: Categorie, hub, pagine indice, sitemap

Per ogni pagina, rispondi SOLO con un JSON array nel formato:
[
  {{"url": "...", "type": "TRANSACTIONAL|INFORMATIONAL|NAVIGATIONAL", "confidence": 0.0-1.0, "signals": ["signal1", "signal2"]}},
  ...
]

Pagine da classificare:
{''.join(pages_text)}

Rispondi SOLO con il JSON array, nessun altro testo."""

        # Try to get AI response
        provider_chain = orchestrator.config.get_provider_chain()

        for provider_type in provider_chain:
            if provider_type == ProviderType.TEMPLATE:
                continue  # Skip template for classification

            try:
                provider = orchestrator._get_provider(provider_type)
                if provider is None:
                    continue

                result = provider.generate(
                    section_key="page_classification",
                    data={},
                    premise="",
                    feedback_examples=[]
                )

                if result.success and result.current_situation:
                    # Parse JSON response
                    response_text = result.current_situation
                    # Extract JSON from response
                    json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                    if json_match:
                        classifications_data = json.loads(json_match.group())

                        classifications = []
                        for cls_data in classifications_data:
                            page_type = PageType.UNKNOWN
                            type_str = cls_data.get('type', '').upper()
                            if type_str == 'TRANSACTIONAL':
                                page_type = PageType.TRANSACTIONAL
                            elif type_str == 'INFORMATIONAL':
                                page_type = PageType.INFORMATIONAL
                            elif type_str == 'NAVIGATIONAL':
                                page_type = PageType.NAVIGATIONAL

                            # Find matching page data
                            page_data = next((p for p in batch if p['url'] == cls_data.get('url')), None)

                            classifications.append(PageClassification(
                                url=cls_data.get('url', ''),
                                page_type=page_type,
                                confidence=float(cls_data.get('confidence', 0.7)),
                                signals=cls_data.get('signals', []),
                                title=page_data.get('title', '') if page_data else '',
                                h1=page_data.get('h1', '') if page_data else '',
                            ))

                        return classifications

            except Exception as e:
                logger.warning(f"Provider {provider_type} failed for classification: {e}")
                continue

        # If all AI providers fail, use heuristics
        return [self._classify_single_heuristic(page) for page in batch]

    def _classify_with_heuristics(self, pages_data: List[Dict]):
        """Classify all pages using URL patterns and content analysis."""
        for page_data in pages_data:
            classification = self._classify_single_heuristic(page_data)
            self._add_classification(classification)

    def _classify_single_heuristic(self, page_data: Dict) -> PageClassification:
        """Classify a single page using heuristics."""
        url = page_data['url'].lower()
        title = page_data.get('title', '').lower()
        h1 = page_data.get('h1', '').lower()
        text = page_data.get('text_snippet', '').lower()
        has_product_schema = page_data.get('has_schema_product', False)

        signals = []
        scores = {
            PageType.TRANSACTIONAL: 0,
            PageType.INFORMATIONAL: 0,
            PageType.NAVIGATIONAL: 0,
        }

        # Check URL patterns
        for pattern in self.TRANSACTIONAL_PATTERNS:
            if re.search(pattern, url):
                scores[PageType.TRANSACTIONAL] += 2
                signals.append(f"URL pattern: {pattern}")
                break

        for pattern in self.INFORMATIONAL_PATTERNS:
            if re.search(pattern, url):
                scores[PageType.INFORMATIONAL] += 2
                signals.append(f"URL pattern: {pattern}")
                break

        for pattern in self.NAVIGATIONAL_PATTERNS:
            if re.search(pattern, url):
                scores[PageType.NAVIGATIONAL] += 2
                signals.append(f"URL pattern: {pattern}")
                break

        # Check content signals
        combined_text = f"{title} {h1} {text}"

        for signal in self.TRANSACTIONAL_SIGNALS:
            if signal in combined_text:
                scores[PageType.TRANSACTIONAL] += 1
                signals.append(f"Content: {signal}")

        for signal in self.INFORMATIONAL_SIGNALS:
            if signal in combined_text:
                scores[PageType.INFORMATIONAL] += 1
                signals.append(f"Content: {signal}")

        # Product schema is strong signal
        if has_product_schema:
            scores[PageType.TRANSACTIONAL] += 3
            signals.append("Has Product schema")

        # Determine winner
        max_score = max(scores.values())
        if max_score == 0:
            page_type = PageType.UNKNOWN
            confidence = 0.3
        else:
            page_type = max(scores, key=scores.get)
            total_score = sum(scores.values())
            confidence = min(0.9, max_score / total_score) if total_score > 0 else 0.5

        return PageClassification(
            url=page_data['url'],
            page_type=page_type,
            confidence=confidence,
            signals=signals[:5],  # Limit signals
            title=page_data.get('title', ''),
            h1=page_data.get('h1', ''),
        )

    def _add_classification(self, classification: PageClassification):
        """Add a classification to the report."""
        self._classifications[classification.url] = classification
        self.report.classified_pages += 1

        if classification.page_type == PageType.TRANSACTIONAL:
            self.report.transactional_count += 1
            self.report.transactional_pages.append(classification)
        elif classification.page_type == PageType.INFORMATIONAL:
            self.report.informational_count += 1
            self.report.informational_pages.append(classification)
        elif classification.page_type == PageType.NAVIGATIONAL:
            self.report.navigational_count += 1
            self.report.navigational_pages.append(classification)
        else:
            self.report.unknown_count += 1
            self.report.unknown_pages.append(classification)

    def get_classification(self, url: str) -> Optional[PageClassification]:
        """Get classification for a specific URL."""
        return self._classifications.get(url)

    def get_summary(self) -> Dict[str, Any]:
        """Get classification summary for reports."""
        return {
            'total_pages': self.report.total_pages,
            'classified_pages': self.report.classified_pages,
            'method': self.report.method,
            'distribution': {
                'transactional': self.report.transactional_count,
                'informational': self.report.informational_count,
                'navigational': self.report.navigational_count,
                'unknown': self.report.unknown_count,
            },
            'transactional_urls': [p.url for p in self.report.transactional_pages],
            'informational_urls': [p.url for p in self.report.informational_pages],
            'navigational_urls': [p.url for p in self.report.navigational_pages],
        }
