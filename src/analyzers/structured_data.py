"""Structured data (Schema.org) analyzer."""

import json
import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from urllib.parse import urlparse

from ..database import CrawlDatabase, PageData


@dataclass
class SchemaIssue:
    """Issue found with structured data."""
    url: str
    schema_type: str
    issue_type: str
    description: str
    severity: str  # 'error', 'warning', 'info'


@dataclass
class SchemaPresence:
    """Presence of schema type on page."""
    url: str
    schema_type: str
    properties: List[str]
    has_required: bool
    missing_required: List[str] = field(default_factory=list)


@dataclass
class StructuredDataReport:
    """Complete structured data analysis report."""
    total_pages_analyzed: int = 0
    pages_with_schema: int = 0
    pages_without_schema: List[str] = field(default_factory=list)

    # Schema types found
    schema_types_found: Dict[str, int] = field(default_factory=dict)  # type -> count

    # Schema presence by page
    schema_by_page: List[SchemaPresence] = field(default_factory=list)

    # Issues
    issues: List[SchemaIssue] = field(default_factory=list)

    # Recommendations
    homepage_missing_schema: bool = False
    product_pages_missing_schema: List[str] = field(default_factory=list)
    article_pages_missing_schema: List[str] = field(default_factory=list)


class StructuredDataAnalyzer:
    """Analyzer for Schema.org structured data."""

    # Required properties for common schema types
    REQUIRED_PROPERTIES = {
        'Product': ['name', 'offers'],
        'Article': ['headline', 'author', 'datePublished'],
        'BlogPosting': ['headline', 'author', 'datePublished'],
        'NewsArticle': ['headline', 'author', 'datePublished'],
        'Organization': ['name'],
        'LocalBusiness': ['name', 'address'],
        'Event': ['name', 'startDate', 'location'],
        'FAQPage': ['mainEntity'],
        'HowTo': ['name', 'step'],
        'Recipe': ['name', 'recipeIngredient', 'recipeInstructions'],
        'VideoObject': ['name', 'description', 'thumbnailUrl', 'uploadDate'],
        'BreadcrumbList': ['itemListElement'],
        'WebSite': ['name', 'url'],
    }

    # Recommended schema by page type (guessed from URL)
    PAGE_TYPE_SCHEMA = {
        'homepage': ['Organization', 'WebSite'],
        'product': ['Product'],
        'article': ['Article', 'BlogPosting'],
        'category': ['CollectionPage', 'ItemList'],
        'contact': ['ContactPage', 'LocalBusiness'],
        'faq': ['FAQPage'],
    }

    def __init__(self, db: CrawlDatabase):
        """Initialize analyzer.

        Args:
            db: Database with crawl data
        """
        self.db = db
        self.report = StructuredDataReport()

    def analyze(self) -> StructuredDataReport:
        """Run structured data analysis.

        Returns:
            StructuredDataReport with all findings
        """
        schema_counts = {}
        homepage_url = None

        for page in self.db.get_all_pages():
            if page.status_code != 200:
                continue

            self.report.total_pages_analyzed += 1

            # Identify homepage
            parsed = urlparse(page.url)
            if parsed.path in ('/', ''):
                homepage_url = page.url

            # Parse structured data
            if page.structured_data_json:
                try:
                    schemas = json.loads(page.structured_data_json)
                    if schemas:
                        self.report.pages_with_schema += 1
                        self._analyze_page_schemas(page.url, schemas, schema_counts)
                    else:
                        self.report.pages_without_schema.append(page.url)
                        self._check_missing_schema(page)
                except json.JSONDecodeError:
                    self.report.pages_without_schema.append(page.url)
            else:
                self.report.pages_without_schema.append(page.url)
                self._check_missing_schema(page)

        self.report.schema_types_found = schema_counts

        # Check homepage
        if homepage_url and homepage_url in self.report.pages_without_schema:
            self.report.homepage_missing_schema = True
            self.report.issues.append(SchemaIssue(
                url=homepage_url,
                schema_type='Organization/WebSite',
                issue_type='missing',
                description='Homepage senza dati strutturati Organization o WebSite',
                severity='warning'
            ))

        return self.report

    def _analyze_page_schemas(self, url: str, schemas: List[Dict], schema_counts: Dict[str, int]):
        """Analyze schemas on a page.

        Args:
            url: Page URL
            schemas: List of schema objects
            schema_counts: Counter for schema types
        """
        for schema in schemas:
            if not isinstance(schema, dict):
                continue

            # Handle @graph
            if '@graph' in schema:
                self._analyze_page_schemas(url, schema['@graph'], schema_counts)
                continue

            schema_type = schema.get('@type', 'Unknown')

            # Handle array types
            if isinstance(schema_type, list):
                schema_type = schema_type[0] if schema_type else 'Unknown'

            # Count
            schema_counts[schema_type] = schema_counts.get(schema_type, 0) + 1

            # Check required properties
            properties = list(schema.keys())
            required = self.REQUIRED_PROPERTIES.get(schema_type, [])
            missing = [prop for prop in required if prop not in properties]

            has_required = len(missing) == 0

            presence = SchemaPresence(
                url=url,
                schema_type=schema_type,
                properties=properties,
                has_required=has_required,
                missing_required=missing
            )
            self.report.schema_by_page.append(presence)

            # Report missing required
            if missing:
                self.report.issues.append(SchemaIssue(
                    url=url,
                    schema_type=schema_type,
                    issue_type='missing_required',
                    description=f'Proprietà obbligatorie mancanti: {", ".join(missing)}',
                    severity='error'
                ))

            # Validate specific types
            self._validate_schema(url, schema_type, schema)

    def _validate_schema(self, url: str, schema_type: str, schema: Dict):
        """Validate specific schema type.

        Args:
            url: Page URL
            schema_type: Schema type
            schema: Schema data
        """
        if schema_type == 'Product':
            self._validate_product(url, schema)
        elif schema_type in ('Article', 'BlogPosting', 'NewsArticle'):
            self._validate_article(url, schema_type, schema)
        elif schema_type == 'BreadcrumbList':
            self._validate_breadcrumb(url, schema)
        elif schema_type == 'FAQPage':
            self._validate_faq(url, schema)

    def _validate_product(self, url: str, schema: Dict):
        """Validate Product schema."""
        offers = schema.get('offers', {})

        if isinstance(offers, dict):
            offers = [offers]

        for offer in offers:
            if not isinstance(offer, dict):
                continue

            # Check price
            if 'price' not in offer and 'priceSpecification' not in offer:
                self.report.issues.append(SchemaIssue(
                    url=url,
                    schema_type='Product',
                    issue_type='missing_price',
                    description='Offerta senza prezzo specificato',
                    severity='warning'
                ))

            # Check currency
            if 'price' in offer and 'priceCurrency' not in offer:
                self.report.issues.append(SchemaIssue(
                    url=url,
                    schema_type='Product',
                    issue_type='missing_currency',
                    description='Prezzo senza valuta specificata',
                    severity='error'
                ))

            # Check availability
            if 'availability' not in offer:
                self.report.issues.append(SchemaIssue(
                    url=url,
                    schema_type='Product',
                    issue_type='missing_availability',
                    description='Disponibilità prodotto non specificata',
                    severity='info'
                ))

    def _validate_article(self, url: str, schema_type: str, schema: Dict):
        """Validate Article schema."""
        # Check image
        if 'image' not in schema:
            self.report.issues.append(SchemaIssue(
                url=url,
                schema_type=schema_type,
                issue_type='missing_image',
                description='Articolo senza immagine nei dati strutturati',
                severity='warning'
            ))

        # Check author format
        author = schema.get('author')
        if author and isinstance(author, str):
            self.report.issues.append(SchemaIssue(
                url=url,
                schema_type=schema_type,
                issue_type='author_format',
                description='Author dovrebbe essere un oggetto Person, non una stringa',
                severity='warning'
            ))

    def _validate_breadcrumb(self, url: str, schema: Dict):
        """Validate BreadcrumbList schema."""
        items = schema.get('itemListElement', [])

        if not items:
            self.report.issues.append(SchemaIssue(
                url=url,
                schema_type='BreadcrumbList',
                issue_type='empty_breadcrumb',
                description='BreadcrumbList vuoto',
                severity='error'
            ))
            return

        # Check positions are sequential
        positions = []
        for item in items:
            if isinstance(item, dict):
                pos = item.get('position')
                if pos is not None:
                    positions.append(int(pos))

        if positions and positions != list(range(1, len(positions) + 1)):
            self.report.issues.append(SchemaIssue(
                url=url,
                schema_type='BreadcrumbList',
                issue_type='invalid_positions',
                description='Posizioni breadcrumb non sequenziali',
                severity='warning'
            ))

    def _validate_faq(self, url: str, schema: Dict):
        """Validate FAQPage schema."""
        main_entity = schema.get('mainEntity', [])

        if not main_entity:
            self.report.issues.append(SchemaIssue(
                url=url,
                schema_type='FAQPage',
                issue_type='empty_faq',
                description='FAQPage senza domande',
                severity='error'
            ))
            return

        # Validate each Q&A
        for i, qa in enumerate(main_entity):
            if not isinstance(qa, dict):
                continue

            if qa.get('@type') != 'Question':
                self.report.issues.append(SchemaIssue(
                    url=url,
                    schema_type='FAQPage',
                    issue_type='invalid_qa_type',
                    description=f'Elemento {i+1} non è di tipo Question',
                    severity='error'
                ))

            if 'name' not in qa:
                self.report.issues.append(SchemaIssue(
                    url=url,
                    schema_type='FAQPage',
                    issue_type='missing_question',
                    description=f'Domanda mancante per elemento {i+1}',
                    severity='error'
                ))

            accepted_answer = qa.get('acceptedAnswer', {})
            if not accepted_answer.get('text'):
                self.report.issues.append(SchemaIssue(
                    url=url,
                    schema_type='FAQPage',
                    issue_type='missing_answer',
                    description=f'Risposta mancante per elemento {i+1}',
                    severity='error'
                ))

    def _check_missing_schema(self, page: PageData):
        """Check if page should have schema based on URL pattern.

        Args:
            page: Page to check
        """
        url_lower = page.url.lower()
        parsed = urlparse(page.url)
        path = parsed.path.lower()

        # Product pages
        product_patterns = ['/product', '/prodotto', '/prodotti', '/shop/', '/item/']
        if any(pattern in path for pattern in product_patterns):
            self.report.product_pages_missing_schema.append(page.url)
            self.report.issues.append(SchemaIssue(
                url=page.url,
                schema_type='Product',
                issue_type='missing',
                description='Pagina prodotto senza schema Product',
                severity='warning'
            ))

        # Article pages
        article_patterns = ['/blog/', '/news/', '/article/', '/post/', '/articolo/']
        if any(pattern in path for pattern in article_patterns):
            self.report.article_pages_missing_schema.append(page.url)
            self.report.issues.append(SchemaIssue(
                url=page.url,
                schema_type='Article',
                issue_type='missing',
                description='Pagina articolo senza schema Article',
                severity='info'
            ))

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of structured data analysis.

        Returns:
            Dictionary with summary data
        """
        error_count = len([i for i in self.report.issues if i.severity == 'error'])
        warning_count = len([i for i in self.report.issues if i.severity == 'warning'])

        return {
            'total_pages': self.report.total_pages_analyzed,
            'pages_with_schema': self.report.pages_with_schema,
            'pages_without_schema': len(self.report.pages_without_schema),
            'schema_types': self.report.schema_types_found,
            'issues': {
                'errors': error_count,
                'warnings': warning_count,
                'total': len(self.report.issues)
            },
            'missing': {
                'homepage': self.report.homepage_missing_schema,
                'products': len(self.report.product_pages_missing_schema),
                'articles': len(self.report.article_pages_missing_schema)
            }
        }

    def get_narrative_summary(self) -> str:
        """Get narrative summary for report.

        Returns:
            Narrative text about structured data
        """
        if self.report.pages_with_schema == 0:
            return (
                "Il sito non presenta dati strutturati implementati. "
                "L'implementazione di Schema.org permetterebbe di ottenere "
                "rich results nei risultati di ricerca, aumentando la visibilità "
                "e il CTR."
            )

        parts = []

        # Overall presence
        coverage = self.report.pages_with_schema / max(self.report.total_pages_analyzed, 1) * 100
        parts.append(
            f"L'analisi dei dati strutturati mostra che il {coverage:.1f}% delle pagine "
            f"({self.report.pages_with_schema} su {self.report.total_pages_analyzed}) "
            f"ha dati strutturati implementati."
        )

        # Types found
        if self.report.schema_types_found:
            types_list = ", ".join(self.report.schema_types_found.keys())
            parts.append(f"I tipi di schema rilevati sono: {types_list}.")

        # Issues
        errors = [i for i in self.report.issues if i.severity == 'error']
        if errors:
            parts.append(
                f"Sono stati rilevati {len(errors)} errori di implementazione "
                f"che potrebbero impedire la corretta visualizzazione dei rich results."
            )

        # Missing recommendations
        if self.report.homepage_missing_schema:
            parts.append(
                "Si consiglia di implementare schema Organization e WebSite sulla homepage."
            )

        if self.report.product_pages_missing_schema:
            parts.append(
                f"Sono state identificate {len(self.report.product_pages_missing_schema)} "
                f"pagine prodotto senza schema Product."
            )

        return " ".join(parts)
