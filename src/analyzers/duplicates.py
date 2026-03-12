"""Duplicate content analyzer using similarity algorithms."""

import json
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from urllib.parse import urlparse

from ..database import CrawlDatabase, PageData
from ..utils.similarity import ContentSimilarity, SimilarityResult


@dataclass
class DuplicateGroup:
    """Group of duplicate/similar pages."""
    canonical_url: str  # Suggested canonical
    urls: List[str]
    similarity: float
    category: str  # 'exact', 'near', 'similar'
    differences: List[str] = field(default_factory=list)
    suggested_action: str = ""


@dataclass
class DuplicateReport:
    """Complete duplicate content analysis report."""
    total_pages_analyzed: int = 0
    exact_duplicates: int = 0  # >95% similarity
    near_duplicates: int = 0  # 85-95% similarity
    similar_pages: int = 0  # 70-85% similarity

    duplicate_groups: List[DuplicateGroup] = field(default_factory=list)

    # Specific patterns
    product_variants: List[DuplicateGroup] = field(default_factory=list)  # Color/size variants
    paginated_duplicates: List[DuplicateGroup] = field(default_factory=list)  # Pagination issues
    parameter_duplicates: List[DuplicateGroup] = field(default_factory=list)  # URL parameter variants

    # Pages wasted on duplicates
    estimated_wasted_pages: int = 0


class DuplicateAnalyzer:
    """Analyzer for duplicate and similar content detection."""

    def __init__(self, db: CrawlDatabase, similarity_threshold: float = 0.85):
        """Initialize analyzer.

        Args:
            db: Database with crawl data
            similarity_threshold: Minimum similarity to consider as duplicate
        """
        self.db = db
        self.similarity_threshold = similarity_threshold
        self.similarity = ContentSimilarity(similarity_threshold)
        self.report = DuplicateReport()

    def analyze(self) -> DuplicateReport:
        """Run duplicate content analysis.

        Returns:
            DuplicateReport with all findings
        """
        from ..utils.helpers import normalize_url

        # Collect all pages with content, deduplicating by normalized URL
        pages_with_content = []
        seen_normalized_urls = set()

        for page in self.db.get_all_pages():
            if page.status_code != 200 or not page.text_content:
                continue

            # Skip very short pages
            if len(page.text_content) < 100:
                continue

            # Skip if we've already seen this URL (after normalization)
            # This handles cases like example.com/ and example.com being the same page
            normalized = normalize_url(page.url)
            if normalized in seen_normalized_urls:
                continue
            seen_normalized_urls.add(normalized)

            pages_with_content.append((page.url, page.text_content))
            self.report.total_pages_analyzed += 1

        if len(pages_with_content) < 2:
            return self.report

        # Find duplicate groups
        duplicate_groups = self.similarity.find_duplicates(pages_with_content)

        # Process groups
        for main_url, similar_results in duplicate_groups.items():
            if not similar_results:
                continue

            # Determine category based on average similarity
            avg_similarity = sum(r.similarity for r in similar_results) / len(similar_results)

            if avg_similarity >= 0.95:
                category = 'exact'
                self.report.exact_duplicates += len(similar_results) + 1
            elif avg_similarity >= 0.85:
                category = 'near'
                self.report.near_duplicates += len(similar_results) + 1
            else:
                category = 'similar'
                self.report.similar_pages += len(similar_results) + 1

            # Collect all URLs in group
            group_urls = [main_url] + [r.url2 for r in similar_results]

            # Determine best canonical (shortest URL, or most linked)
            canonical_url = self._select_canonical(group_urls)

            # Collect differences
            all_differences = []
            for result in similar_results:
                if result.differences:
                    all_differences.extend(result.differences)

            # Determine action
            action = self._suggest_action(category, group_urls, all_differences)

            group = DuplicateGroup(
                canonical_url=canonical_url,
                urls=group_urls,
                similarity=avg_similarity,
                category=category,
                differences=list(set(all_differences))[:10],  # Top 10 unique differences
                suggested_action=action
            )

            self.report.duplicate_groups.append(group)

            # Categorize by pattern
            self._categorize_group(group)

        # Calculate wasted pages
        self.report.estimated_wasted_pages = (
            self.report.exact_duplicates +
            self.report.near_duplicates
        ) - len(self.report.duplicate_groups)

        return self.report

    def _select_canonical(self, urls: List[str]) -> str:
        """Select best URL to be the canonical.

        Args:
            urls: List of duplicate URLs

        Returns:
            Best URL to be canonical
        """
        if not urls:
            return ""

        # Scoring function
        def score_url(url: str) -> Tuple[int, int, int]:
            parsed = urlparse(url)

            # Prefer shorter paths
            path_length = len(parsed.path)

            # Prefer no query parameters
            has_params = 1 if parsed.query else 0

            # Count internal links (more = better)
            incoming = len(self.db.get_internal_links_to(url))

            return (-incoming, has_params, path_length)

        return min(urls, key=score_url)

    def _suggest_action(self, category: str, urls: List[str], differences: List[str]) -> str:
        """Suggest action for duplicate group.

        Args:
            category: Duplicate category
            urls: URLs in the group
            differences: Differences found

        Returns:
            Suggested action string
        """
        if category == 'exact':
            return (
                "Implementare tag canonical verso la versione principale, "
                "oppure consolidare le pagine in una sola."
            )
        elif category == 'near':
            # Check if it's likely product variants
            variant_keywords = ['colore', 'color', 'taglia', 'size', 'variante', 'variant']
            is_variant = any(
                kw in ' '.join(differences).lower()
                for kw in variant_keywords
            )

            if is_variant:
                return (
                    "Queste pagine sembrano varianti di prodotto. "
                    "Implementare canonical verso la pagina prodotto principale, "
                    "o differenziare i contenuti con descrizioni uniche per ogni variante."
                )
            else:
                return (
                    "Differenziare i contenuti delle pagine aggiungendo testo unico, "
                    "oppure implementare canonical se una è la versione principale."
                )
        else:
            return (
                "Valutare se il contenuto simile è intenzionale. "
                "Se non necessario, differenziare le pagine."
            )

    def _categorize_group(self, group: DuplicateGroup):
        """Categorize duplicate group by pattern.

        Args:
            group: DuplicateGroup to categorize
        """
        urls = group.urls

        # Check for product variants (color, size in URL)
        variant_patterns = ['color', 'colore', 'size', 'taglia', 'variant']
        is_variant = any(
            any(pattern in url.lower() for pattern in variant_patterns)
            for url in urls
        )

        if is_variant:
            self.report.product_variants.append(group)
            return

        # Check for pagination
        pagination_patterns = ['page=', '/page/', 'pag=', 'pagina=']
        is_pagination = any(
            any(pattern in url.lower() for pattern in pagination_patterns)
            for url in urls
        )

        if is_pagination:
            self.report.paginated_duplicates.append(group)
            return

        # Check for parameter variants
        parsed_urls = [urlparse(url) for url in urls]
        has_params = [bool(p.query) for p in parsed_urls]

        if any(has_params) and not all(has_params):
            self.report.parameter_duplicates.append(group)
            return

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of duplicate analysis.

        Returns:
            Dictionary with summary data
        """
        # Prepare detailed group information for AI analysis
        groups_detail = []
        for group in self.report.duplicate_groups[:15]:  # Limit to 15 groups for context
            groups_detail.append({
                'category': group.category,
                'similarity': round(group.similarity * 100, 1),
                'canonical_suggested': group.canonical_url,
                'urls': group.urls[:5],  # First 5 URLs per group
                'total_urls_in_group': len(group.urls),
                'differences': group.differences[:5] if group.differences else [],
                'suggested_action': group.suggested_action
            })

        return {
            'total_analyzed': self.report.total_pages_analyzed,
            'duplicates': {
                'exact': self.report.exact_duplicates,
                'near': self.report.near_duplicates,
                'similar': self.report.similar_pages
            },
            'groups': len(self.report.duplicate_groups),
            'groups_detail': groups_detail,  # Detailed info for each group
            'patterns': {
                'product_variants': len(self.report.product_variants),
                'pagination': len(self.report.paginated_duplicates),
                'parameters': len(self.report.parameter_duplicates)
            },
            'product_variant_groups': [
                {
                    'urls': g.urls[:5],
                    'similarity': round(g.similarity * 100, 1)
                } for g in self.report.product_variants[:5]
            ],
            'pagination_groups': [
                {
                    'urls': g.urls[:5],
                    'similarity': round(g.similarity * 100, 1)
                } for g in self.report.paginated_duplicates[:5]
            ],
            'parameter_groups': [
                {
                    'urls': g.urls[:5],
                    'similarity': round(g.similarity * 100, 1)
                } for g in self.report.parameter_duplicates[:5]
            ],
            'estimated_wasted': self.report.estimated_wasted_pages
        }

    def get_narrative_summary(self) -> str:
        """Get narrative summary for report.

        Returns:
            Narrative text about duplicate content
        """
        if not self.report.duplicate_groups:
            return (
                "L'analisi dei contenuti non ha rilevato problemi significativi di duplicazione. "
                "Le pagine del sito presentano contenuti sufficientemente differenziati."
            )

        parts = []

        if self.report.exact_duplicates > 0:
            parts.append(
                f"Sono state individuate {self.report.exact_duplicates} pagine con contenuto "
                f"praticamente identico, distribuite in {len([g for g in self.report.duplicate_groups if g.category == 'exact'])} "
                f"gruppi di duplicati."
            )

        if self.report.near_duplicates > 0:
            parts.append(
                f"Inoltre, sono presenti {self.report.near_duplicates} pagine con contenuto "
                f"quasi duplicato (similarità 85-95%), che differiscono solo per dettagli minimi."
            )

        if self.report.product_variants:
            parts.append(
                f"In particolare, {len(self.report.product_variants)} gruppi sembrano essere "
                f"varianti di prodotto (es. stesso prodotto in colori diversi) con descrizioni identiche."
            )

        if self.report.estimated_wasted_pages > 0:
            parts.append(
                f"Questa situazione comporta uno 'spreco' stimato di circa {self.report.estimated_wasted_pages} "
                f"pagine che potrebbero essere consolidate o differenziate per massimizzare "
                f"il potenziale di posizionamento."
            )

        return " ".join(parts)
