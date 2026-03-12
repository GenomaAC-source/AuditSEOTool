"""Strategic Linking Analyzer - analyzes link flow between page types."""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict

from .page_classifier import PageClassifier, PageType, ClassificationReport

logger = logging.getLogger(__name__)


@dataclass
class LinkFlow:
    """Represents link flow between two page types."""
    source_type: PageType
    target_type: PageType
    count: int = 0
    links: List[Tuple[str, str]] = field(default_factory=list)  # (source_url, target_url)


@dataclass
class HubPage:
    """A page that acts as a link hub."""
    url: str
    page_type: PageType
    outgoing_links: int
    incoming_links: int
    links_to_transactional: int
    links_to_informational: int
    links_to_navigational: int
    hub_score: float  # Combined measure of connectivity


@dataclass
class IsolatedPage:
    """A page that lacks strategic linking."""
    url: str
    page_type: PageType
    issue: str  # Description of the isolation issue
    incoming_from_info: int
    incoming_from_trans: int
    outgoing_to_info: int
    outgoing_to_trans: int


@dataclass
class StrategicLinkingReport:
    """Complete strategic linking analysis report."""

    # Page classification summary
    classification_method: str = "ai"
    page_type_distribution: Dict[str, int] = field(default_factory=dict)

    # Link flow matrix (source_type -> target_type -> count)
    link_flow_matrix: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # Detailed flow data
    info_to_trans_links: List[Tuple[str, str]] = field(default_factory=list)
    trans_to_info_links: List[Tuple[str, str]] = field(default_factory=list)

    # Flow metrics
    info_to_trans_count: int = 0
    trans_to_info_count: int = 0
    info_to_trans_ratio: float = 0.0  # How much info pages support trans pages

    # Hub pages (top link distributors)
    hub_pages: List[HubPage] = field(default_factory=list)

    # Isolated pages (lacking strategic links)
    isolated_transactional: List[IsolatedPage] = field(default_factory=list)  # Trans pages without info support
    isolated_informational: List[IsolatedPage] = field(default_factory=list)  # Info pages not linking to trans

    # Issues and recommendations
    issues: List[Dict[str, Any]] = field(default_factory=list)

    # Overall scores
    strategic_linking_score: float = 0.0  # 0-100


class StrategicLinkingAnalyzer:
    """Analyzes internal linking from a strategic SEO perspective."""

    def __init__(self, db, classification_report: ClassificationReport):
        """Initialize analyzer.

        Args:
            db: CrawlDatabase instance
            classification_report: Page classification report from PageClassifier
        """
        self.db = db
        self.classification = classification_report
        self.report = StrategicLinkingReport()

        # Build URL to type mapping
        self.url_type_map = classification_report.get_url_type_map()

        # Link data structures
        self.outgoing_links: Dict[str, List[str]] = defaultdict(list)  # url -> [target_urls]
        self.incoming_links: Dict[str, List[str]] = defaultdict(list)  # url -> [source_urls]

    def analyze(self) -> StrategicLinkingReport:
        """Run complete strategic linking analysis."""
        logger.info("Starting strategic linking analysis...")

        # Store classification info
        self.report.classification_method = self.classification.method
        self.report.page_type_distribution = {
            'transactional': self.classification.transactional_count,
            'informational': self.classification.informational_count,
            'navigational': self.classification.navigational_count,
            'unknown': self.classification.unknown_count,
        }

        # Build link graph
        self._build_link_graph()

        # Analyze link flow between types
        self._analyze_link_flow()

        # Find hub pages
        self._find_hub_pages()

        # Find isolated pages
        self._find_isolated_pages()

        # Calculate strategic score
        self._calculate_strategic_score()

        # Generate issues and recommendations
        self._generate_issues()

        logger.info(f"Strategic linking analysis complete. Score: {self.report.strategic_linking_score:.1f}")
        return self.report

    def _build_link_graph(self):
        """Build internal link graph from database."""
        for page in self.db.get_all_pages():
            if page.status_code != 200 or not page.internal_links_json:
                continue

            try:
                links = json.loads(page.internal_links_json)
                for link in links:
                    target_url = link.get('url', '')
                    if target_url and target_url in self.url_type_map:
                        self.outgoing_links[page.url].append(target_url)
                        self.incoming_links[target_url].append(page.url)
            except json.JSONDecodeError:
                pass

    def _analyze_link_flow(self):
        """Analyze link flow between page types."""
        # Initialize flow matrix
        types = ['transactional', 'informational', 'navigational', 'unknown']
        flow_matrix = {t: {t2: 0 for t2 in types} for t in types}

        # Count flows
        for source_url, targets in self.outgoing_links.items():
            source_type = self.url_type_map.get(source_url, PageType.UNKNOWN)
            source_type_str = source_type.value

            for target_url in targets:
                target_type = self.url_type_map.get(target_url, PageType.UNKNOWN)
                target_type_str = target_type.value

                flow_matrix[source_type_str][target_type_str] += 1

                # Track specific important flows
                if source_type == PageType.INFORMATIONAL and target_type == PageType.TRANSACTIONAL:
                    self.report.info_to_trans_links.append((source_url, target_url))
                elif source_type == PageType.TRANSACTIONAL and target_type == PageType.INFORMATIONAL:
                    self.report.trans_to_info_links.append((source_url, target_url))

        self.report.link_flow_matrix = flow_matrix
        self.report.info_to_trans_count = len(self.report.info_to_trans_links)
        self.report.trans_to_info_count = len(self.report.trans_to_info_links)

        # Calculate ratio (info pages supporting trans pages)
        total_info_outgoing = sum(flow_matrix['informational'].values())
        if total_info_outgoing > 0:
            self.report.info_to_trans_ratio = self.report.info_to_trans_count / total_info_outgoing

    def _find_hub_pages(self):
        """Identify pages that act as link hubs."""
        hub_candidates = []

        for url in self.url_type_map:
            outgoing = self.outgoing_links.get(url, [])
            incoming = self.incoming_links.get(url, [])

            if len(outgoing) < 3 and len(incoming) < 3:
                continue  # Not a significant hub

            # Count links by target type
            links_to_trans = sum(1 for u in outgoing if self.url_type_map.get(u) == PageType.TRANSACTIONAL)
            links_to_info = sum(1 for u in outgoing if self.url_type_map.get(u) == PageType.INFORMATIONAL)
            links_to_nav = sum(1 for u in outgoing if self.url_type_map.get(u) == PageType.NAVIGATIONAL)

            # Calculate hub score (weighted by strategic value)
            # Linking to transactional is more valuable from info pages
            page_type = self.url_type_map.get(url, PageType.UNKNOWN)

            if page_type == PageType.INFORMATIONAL:
                hub_score = links_to_trans * 2 + links_to_info + len(incoming) * 0.5
            elif page_type == PageType.NAVIGATIONAL:
                hub_score = links_to_trans * 1.5 + links_to_info * 1.5 + len(incoming) * 0.5
            else:
                hub_score = len(outgoing) + len(incoming) * 0.5

            hub_candidates.append(HubPage(
                url=url,
                page_type=page_type,
                outgoing_links=len(outgoing),
                incoming_links=len(incoming),
                links_to_transactional=links_to_trans,
                links_to_informational=links_to_info,
                links_to_navigational=links_to_nav,
                hub_score=hub_score
            ))

        # Sort by hub score and keep top 20
        hub_candidates.sort(key=lambda x: x.hub_score, reverse=True)
        self.report.hub_pages = hub_candidates[:20]

    def _find_isolated_pages(self):
        """Find pages lacking strategic internal linking."""

        # Check transactional pages not supported by informational content
        for page in self.classification.transactional_pages:
            incoming = self.incoming_links.get(page.url, [])

            incoming_from_info = sum(
                1 for u in incoming
                if self.url_type_map.get(u) == PageType.INFORMATIONAL
            )
            incoming_from_trans = sum(
                1 for u in incoming
                if self.url_type_map.get(u) == PageType.TRANSACTIONAL
            )

            outgoing = self.outgoing_links.get(page.url, [])
            outgoing_to_info = sum(
                1 for u in outgoing
                if self.url_type_map.get(u) == PageType.INFORMATIONAL
            )
            outgoing_to_trans = sum(
                1 for u in outgoing
                if self.url_type_map.get(u) == PageType.TRANSACTIONAL
            )

            # Transactional page without informational support
            if incoming_from_info == 0 and len(incoming) < 3:
                self.report.isolated_transactional.append(IsolatedPage(
                    url=page.url,
                    page_type=PageType.TRANSACTIONAL,
                    issue="Pagina transazionale senza supporto da contenuti informativi",
                    incoming_from_info=incoming_from_info,
                    incoming_from_trans=incoming_from_trans,
                    outgoing_to_info=outgoing_to_info,
                    outgoing_to_trans=outgoing_to_trans
                ))

        # Check informational pages not linking to transactional
        for page in self.classification.informational_pages:
            outgoing = self.outgoing_links.get(page.url, [])

            outgoing_to_trans = sum(
                1 for u in outgoing
                if self.url_type_map.get(u) == PageType.TRANSACTIONAL
            )
            outgoing_to_info = sum(
                1 for u in outgoing
                if self.url_type_map.get(u) == PageType.INFORMATIONAL
            )

            incoming = self.incoming_links.get(page.url, [])
            incoming_from_info = sum(
                1 for u in incoming
                if self.url_type_map.get(u) == PageType.INFORMATIONAL
            )
            incoming_from_trans = sum(
                1 for u in incoming
                if self.url_type_map.get(u) == PageType.TRANSACTIONAL
            )

            # Informational page not linking to any transactional
            if outgoing_to_trans == 0 and len(outgoing) > 0:
                self.report.isolated_informational.append(IsolatedPage(
                    url=page.url,
                    page_type=PageType.INFORMATIONAL,
                    issue="Pagina informativa che non valorizza contenuti transazionali",
                    incoming_from_info=incoming_from_info,
                    incoming_from_trans=incoming_from_trans,
                    outgoing_to_info=outgoing_to_info,
                    outgoing_to_trans=outgoing_to_trans
                ))

        # Limit lists
        self.report.isolated_transactional = self.report.isolated_transactional[:50]
        self.report.isolated_informational = self.report.isolated_informational[:50]

    def _calculate_strategic_score(self):
        """Calculate overall strategic linking score (0-100)."""
        score = 50  # Base score

        total_trans = self.classification.transactional_count
        total_info = self.classification.informational_count

        if total_trans == 0 and total_info == 0:
            self.report.strategic_linking_score = 50
            return

        # Factor 1: Info pages supporting trans pages (up to +20)
        if total_info > 0 and total_trans > 0:
            # What % of trans pages receive links from info pages?
            trans_with_info_support = set()
            for source, target in self.report.info_to_trans_links:
                trans_with_info_support.add(target)

            support_ratio = len(trans_with_info_support) / total_trans if total_trans > 0 else 0
            score += support_ratio * 20

        # Factor 2: Info to trans ratio (up to +15)
        # Ideal: at least 30% of info outgoing links go to trans
        if self.report.info_to_trans_ratio >= 0.3:
            score += 15
        elif self.report.info_to_trans_ratio >= 0.15:
            score += 10
        elif self.report.info_to_trans_ratio >= 0.05:
            score += 5

        # Factor 3: Penalize isolated pages (up to -25)
        isolated_trans_ratio = len(self.report.isolated_transactional) / total_trans if total_trans > 0 else 0
        isolated_info_ratio = len(self.report.isolated_informational) / total_info if total_info > 0 else 0

        score -= isolated_trans_ratio * 15
        score -= isolated_info_ratio * 10

        # Factor 4: Hub page presence (up to +10)
        info_hubs = sum(1 for h in self.report.hub_pages if h.page_type == PageType.INFORMATIONAL)
        nav_hubs = sum(1 for h in self.report.hub_pages if h.page_type == PageType.NAVIGATIONAL)

        if info_hubs >= 3:
            score += 5
        if nav_hubs >= 2:
            score += 5

        # Clamp score
        self.report.strategic_linking_score = max(0, min(100, score))

    def _generate_issues(self):
        """Generate actionable issues and recommendations."""
        issues = []

        # Issue: Many isolated transactional pages
        if len(self.report.isolated_transactional) > 5:
            issues.append({
                'severity': 'critical',
                'title': 'Pagine transazionali isolate',
                'description': f"{len(self.report.isolated_transactional)} pagine transazionali non ricevono link da contenuti informativi",
                'recommendation': "Creare contenuti informativi (guide, blog post) che linkano alle pagine prodotto/servizio",
                'affected_pages': [p.url for p in self.report.isolated_transactional[:5]]
            })

        # Issue: Info pages not supporting trans
        if len(self.report.isolated_informational) > 5:
            issues.append({
                'severity': 'warning',
                'title': 'Contenuti informativi non valorizzanti',
                'description': f"{len(self.report.isolated_informational)} pagine informative non linkano a contenuti transazionali",
                'recommendation': "Aggiungere CTA e link contestuali verso prodotti/servizi nei contenuti informativi",
                'affected_pages': [p.url for p in self.report.isolated_informational[:5]]
            })

        # Issue: Low info-to-trans ratio
        if self.report.info_to_trans_ratio < 0.1 and self.classification.informational_count > 5:
            issues.append({
                'severity': 'warning',
                'title': 'Scarso supporto informativo ai contenuti commerciali',
                'description': f"Solo il {self.report.info_to_trans_ratio*100:.1f}% dei link da pagine informative porta a pagine transazionali",
                'recommendation': "Aumentare i link interni dalle guide/blog verso le pagine di prodotto e servizio"
            })

        # Issue: No clear hub pages
        if len(self.report.hub_pages) < 3:
            issues.append({
                'severity': 'info',
                'title': 'Mancanza di pagine hub',
                'description': "Non sono state identificate pagine che fungono da hub per distribuire link equity",
                'recommendation': "Creare pagine pillar/cornerstone che aggregano e linkano contenuti correlati"
            })

        self.report.issues = issues

    def get_summary(self) -> Dict[str, Any]:
        """Get analysis summary for reports."""
        return {
            'classification_method': self.report.classification_method,
            'page_type_distribution': self.report.page_type_distribution,
            'link_flow_matrix': self.report.link_flow_matrix,
            'info_to_trans_count': self.report.info_to_trans_count,
            'trans_to_info_count': self.report.trans_to_info_count,
            'info_to_trans_ratio': self.report.info_to_trans_ratio,
            'strategic_linking_score': self.report.strategic_linking_score,
            'hub_pages_count': len(self.report.hub_pages),
            'isolated_transactional_count': len(self.report.isolated_transactional),
            'isolated_informational_count': len(self.report.isolated_informational),
            'hub_pages': [
                {
                    'url': h.url,
                    'type': h.page_type.value,
                    'outgoing': h.outgoing_links,
                    'incoming': h.incoming_links,
                    'to_trans': h.links_to_transactional,
                    'hub_score': h.hub_score
                }
                for h in self.report.hub_pages[:10]
            ],
            'isolated_transactional': [
                {'url': p.url, 'issue': p.issue}
                for p in self.report.isolated_transactional[:10]
            ],
            'isolated_informational': [
                {'url': p.url, 'issue': p.issue}
                for p in self.report.isolated_informational[:10]
            ],
            'issues': self.report.issues,
            'info_to_trans_links_sample': self.report.info_to_trans_links[:20],
        }
