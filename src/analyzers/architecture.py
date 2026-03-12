"""Architecture analyzer for site structure, URLs, navigation, and hreflang."""

import json
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass, field
from collections import defaultdict

from ..database import CrawlDatabase, PageData
from ..utils.helpers import (
    url_uses_underscore, url_has_uppercase, url_has_double_slash,
    has_url_parameters, get_url_depth, validate_hreflang_code,
    normalize_url
)


@dataclass
class UrlIssue:
    """URL issue found during analysis."""
    url: str
    issue_type: str
    description: str
    severity: str  # 'high', 'medium', 'low'


@dataclass
class HreflangIssue:
    """Hreflang issue found during analysis."""
    url: str
    issue_type: str
    description: str
    affected_languages: List[str] = field(default_factory=list)


@dataclass
class ArchitectureReport:
    """Complete architecture analysis report."""
    # Site structure
    total_pages: int = 0
    depth_distribution: Dict[int, int] = field(default_factory=dict)
    deep_pages: List[Tuple[str, int]] = field(default_factory=list)  # (url, depth)
    orphan_pages: List[str] = field(default_factory=list)
    site_sections: Dict[str, int] = field(default_factory=dict)  # section -> page count

    # URL analysis
    url_issues: List[UrlIssue] = field(default_factory=list)
    urls_with_underscore: int = 0
    urls_with_uppercase: int = 0
    urls_with_double_slash: int = 0
    urls_with_parameters: int = 0

    # Canonical analysis (based on Google guidelines)
    pages_without_canonical: List[str] = field(default_factory=list)
    canonical_mismatches: List[Tuple[str, str]] = field(default_factory=list)  # (url, canonical)
    canonical_to_404: List[Tuple[str, str]] = field(default_factory=list)
    canonical_to_redirect: List[Tuple[str, str, int]] = field(default_factory=list)  # (url, canonical, redirect_code)
    canonical_relative_urls: List[Tuple[str, str]] = field(default_factory=list)  # (url, relative_canonical)
    canonical_http_on_https: List[Tuple[str, str]] = field(default_factory=list)  # (url, http_canonical)
    canonical_not_in_sitemap: List[Tuple[str, str]] = field(default_factory=list)  # (url, canonical)
    canonical_chains: List[List[str]] = field(default_factory=list)
    # Classification of mismatches
    canonical_intentional: List[Dict] = field(default_factory=list)  # Likely intentional (variants, tracking params)
    canonical_errors: List[Dict] = field(default_factory=list)  # Likely errors

    # Hreflang analysis
    languages_found: Set[str] = field(default_factory=set)
    hreflang_issues: List[HreflangIssue] = field(default_factory=list)
    non_reciprocal_hreflang: List[Dict] = field(default_factory=list)
    invalid_hreflang_codes: List[Tuple[str, str]] = field(default_factory=list)  # (url, code)
    x_default_issues: List[Dict] = field(default_factory=list)

    # Navigation
    menu_links: List[Dict] = field(default_factory=list)
    pages_not_in_menu: List[str] = field(default_factory=list)
    broken_menu_links: List[str] = field(default_factory=list)


class ArchitectureAnalyzer:
    """Analyzer for site architecture, URLs, and hreflang."""

    def __init__(self, db: CrawlDatabase):
        """Initialize analyzer.

        Args:
            db: Database with crawl data
        """
        self.db = db
        self.report = ArchitectureReport()

    def analyze(self) -> ArchitectureReport:
        """Run complete architecture analysis.

        Returns:
            ArchitectureReport with all findings
        """
        self._analyze_structure()
        self._analyze_urls()
        self._analyze_canonicals()
        self._analyze_hreflang()
        self._analyze_navigation()

        return self.report

    def _analyze_structure(self):
        """Analyze site structure and depth."""
        depth_counts = defaultdict(int)
        section_counts = defaultdict(int)
        all_urls = set()
        linked_urls = set()

        for page in self.db.get_all_pages():
            if page.status_code != 200:
                continue

            all_urls.add(page.url)
            self.report.total_pages += 1

            # Track depth
            depth = page.depth
            depth_counts[depth] += 1

            if depth > 3:
                self.report.deep_pages.append((page.url, depth))

            # Track sections
            parsed = urlparse(page.url)
            path_parts = parsed.path.strip('/').split('/')
            if path_parts and path_parts[0]:
                section_counts[path_parts[0]] += 1

            # Track linked URLs
            if page.internal_links_json:
                try:
                    links = json.loads(page.internal_links_json)
                    for link in links:
                        linked_urls.add(normalize_url(link.get('url', '')))
                except json.JSONDecodeError:
                    pass

        self.report.depth_distribution = dict(depth_counts)
        self.report.site_sections = dict(section_counts)

        # Find orphan pages (pages with no internal links pointing to them)
        # We need to check the links table
        for url in all_urls:
            incoming_links = self.db.get_internal_links_to(url)
            if not incoming_links and urlparse(url).path not in ('/', ''):
                self.report.orphan_pages.append(url)

    def _analyze_urls(self):
        """Analyze URL structure and issues."""
        for page in self.db.get_all_pages():
            url = page.url

            # Check for underscores
            if url_uses_underscore(url):
                self.report.urls_with_underscore += 1
                self.report.url_issues.append(UrlIssue(
                    url=url,
                    issue_type='underscore',
                    description='URL contiene underscore (_) invece di dash (-)',
                    severity='low'
                ))

            # Check for uppercase
            if url_has_uppercase(url):
                self.report.urls_with_uppercase += 1
                self.report.url_issues.append(UrlIssue(
                    url=url,
                    issue_type='uppercase',
                    description='URL contiene caratteri maiuscoli',
                    severity='low'
                ))

            # Check for double slashes
            if url_has_double_slash(url):
                self.report.urls_with_double_slash += 1
                self.report.url_issues.append(UrlIssue(
                    url=url,
                    issue_type='double_slash',
                    description='URL contiene doppi slash (//)',
                    severity='medium'
                ))

            # Check for parameters
            if has_url_parameters(url):
                self.report.urls_with_parameters += 1

    def _analyze_canonicals(self):
        """Analyze canonical tags based on Google's guidelines.

        Logic for mismatch validation:
        When page A has canonical pointing to B (where A ≠ B):
        1. Check if B exists and returns 200
        2. Check if B has self-referencing canonical (B → B)
        3. If both conditions are met → valid implementation
        4. Otherwise → error (404, redirect, or canonical chain)

        Reference: https://developers.google.com/search/docs/crawling-indexing/canonicalization
        """
        # Build comprehensive map of all pages: url -> {status, canonical, raw_url}
        page_data = {}
        for page in self.db.get_all_pages():
            normalized = normalize_url(page.url)
            page_data[normalized] = {
                'status': page.status_code,
                'canonical': page.canonical.strip() if page.canonical else None,
                'canonical_normalized': normalize_url(page.canonical.strip()) if page.canonical else None,
                'raw_url': page.url
            }

        # Get sitemap URLs for cross-checking
        sitemap_urls = set()
        try:
            for page in self.db.get_all_pages():
                if page.in_sitemap:
                    sitemap_urls.add(normalize_url(page.url))
        except:
            pass

        for page in self.db.get_all_pages():
            if page.status_code != 200:
                continue

            page_url = page.url
            normalized_page_url = normalize_url(page_url)
            page_is_https = page_url.startswith('https://')

            if not page.canonical:
                # Missing canonical - should have at least self-referencing
                self.report.pages_without_canonical.append(page_url)
                continue

            raw_canonical = page.canonical.strip()

            # Check 1: Relative URL (Google recommends absolute URLs)
            if not raw_canonical.startswith('http://') and not raw_canonical.startswith('https://'):
                self.report.canonical_relative_urls.append((page_url, raw_canonical))
                from urllib.parse import urljoin
                canonical = normalize_url(urljoin(page_url, raw_canonical))
            else:
                canonical = normalize_url(raw_canonical)

            # Check 2: HTTP canonical on HTTPS page (Google prefers HTTPS)
            if page_is_https and raw_canonical.startswith('http://') and not raw_canonical.startswith('https://'):
                self.report.canonical_http_on_https.append((page_url, raw_canonical))

            # Self-referencing canonical (including trailing slash variants) - OK
            if canonical == normalized_page_url:
                continue

            # === MISMATCH DETECTED: page A has canonical → B ===
            # Now we need to validate B

            self.report.canonical_mismatches.append((page_url, raw_canonical))

            # Get data for the canonical target (B)
            target_data = page_data.get(canonical)

            if target_data is None:
                # Canonical points to URL not crawled - can't fully validate
                # This might be external or not discovered
                mismatch_info = {
                    'url': page_url,
                    'canonical': raw_canonical,
                    'issue': 'canonical_not_crawled',
                    'severity': 'info',
                    'detail': 'La pagina canonical non è stata crawlata, impossibile verificare'
                }
                self.report.canonical_errors.append(mismatch_info)
                continue

            target_status = target_data['status']
            target_canonical = target_data['canonical_normalized']

            # Check 3: Canonical target (B) returns 404
            if target_status == 404:
                self.report.canonical_to_404.append((page_url, raw_canonical))
                self.report.canonical_errors.append({
                    'url': page_url,
                    'canonical': raw_canonical,
                    'issue': 'points_to_404',
                    'severity': 'critical',
                    'detail': f'Il canonical punta a una pagina 404'
                })
                continue

            # Check 4: Canonical target (B) is a redirect
            if target_status in (301, 302, 307, 308):
                self.report.canonical_to_redirect.append((page_url, raw_canonical, target_status))
                self.report.canonical_errors.append({
                    'url': page_url,
                    'canonical': raw_canonical,
                    'issue': 'points_to_redirect',
                    'severity': 'warning',
                    'detail': f'Il canonical punta a un redirect ({target_status})'
                })
                continue

            # Check 5: Canonical target (B) should have self-referencing canonical
            if target_status == 200 and target_canonical:
                if target_canonical == canonical:
                    # B has self-referencing canonical → VALID implementation
                    # This is correct: A→B and B→B
                    mismatch_info = {
                        'url': page_url,
                        'canonical': raw_canonical,
                        'reason': self._get_mismatch_reason(page_url, raw_canonical),
                        'validated': True,
                        'detail': 'Implementazione corretta: il canonical è autoreferenziale'
                    }
                    self.report.canonical_intentional.append(mismatch_info)
                    continue
                elif target_canonical == normalized_page_url:
                    # B points back to A → potential loop or reciprocal (unusual)
                    self.report.canonical_errors.append({
                        'url': page_url,
                        'canonical': raw_canonical,
                        'issue': 'reciprocal_canonical',
                        'severity': 'warning',
                        'detail': f'Canonical reciproco: A→B e B→A'
                    })
                    continue
                else:
                    # B points to C → canonical chain
                    self.report.canonical_chains.append([page_url, raw_canonical, target_data['canonical']])
                    self.report.canonical_errors.append({
                        'url': page_url,
                        'canonical': raw_canonical,
                        'issue': 'canonical_chain',
                        'severity': 'warning',
                        'detail': f'Catena di canonical: questa pagina → {raw_canonical} → {target_data["canonical"]}'
                    })
                    continue

            # Check 6: Canonical not in sitemap (weak signal)
            if sitemap_urls and canonical not in sitemap_urls:
                self.report.canonical_not_in_sitemap.append((page_url, raw_canonical))

            # If we get here, classify based on URL patterns
            mismatch_info = {
                'url': page_url,
                'canonical': raw_canonical,
            }

            if self._is_likely_intentional_canonical(page_url, raw_canonical):
                mismatch_info['reason'] = self._get_mismatch_reason(page_url, raw_canonical)
                self.report.canonical_intentional.append(mismatch_info)
            else:
                mismatch_info['issue'] = 'unexpected_mismatch'
                mismatch_info['severity'] = 'warning'
                self.report.canonical_errors.append(mismatch_info)

    def _is_likely_intentional_canonical(self, page_url: str, canonical: str) -> bool:
        """Determine if a canonical mismatch is likely intentional.

        Intentional cases include:
        - Product variants pointing to main product
        - URLs with tracking parameters pointing to clean URL
        - Paginated pages pointing to first page
        - Print/mobile versions pointing to main version
        """
        from urllib.parse import urlparse, parse_qs

        page_parsed = urlparse(page_url)
        canonical_parsed = urlparse(canonical)

        # Same domain required for intentional
        if page_parsed.netloc != canonical_parsed.netloc:
            return False

        # Case 1: URL with parameters pointing to same path without parameters
        page_params = parse_qs(page_parsed.query)
        canonical_params = parse_qs(canonical_parsed.query)

        if page_params and not canonical_params and page_parsed.path == canonical_parsed.path:
            return True  # Likely tracking parameter cleanup

        # Case 2: Pagination - page with /page/N or ?page=N pointing to first page
        if '/page/' in page_url or 'page=' in page_url:
            return True

        # Case 3: Product variants (color, size) - similar path structure
        # e.g., /product/shirt-blue -> /product/shirt
        page_path_parts = page_parsed.path.rstrip('/').split('/')
        canonical_path_parts = canonical_parsed.path.rstrip('/').split('/')

        if len(page_path_parts) == len(canonical_path_parts):
            # Check if paths differ only in last segment (variant indicator)
            if page_path_parts[:-1] == canonical_path_parts[:-1]:
                # Last segments are similar (e.g., shirt-blue vs shirt)
                if canonical_path_parts[-1] in page_path_parts[-1]:
                    return True

        # Note: Trailing slash differences are now handled earlier in _analyze_canonicals()
        # and are not considered mismatches at all, so we don't need to check here

        return False

    def _get_mismatch_reason(self, page_url: str, canonical: str) -> str:
        """Get human-readable reason for intentional mismatch."""
        from urllib.parse import urlparse, parse_qs

        page_parsed = urlparse(page_url)
        canonical_parsed = urlparse(canonical)

        page_params = parse_qs(page_parsed.query)
        canonical_params = parse_qs(canonical_parsed.query)

        if page_params and not canonical_params:
            return "tracking_parameters"
        if '/page/' in page_url or 'page=' in page_url:
            return "pagination"

        return "product_variant"

    def _analyze_hreflang(self):
        """Analyze hreflang implementation."""
        # Build hreflang map: url -> {lang: href}
        hreflang_map: Dict[str, Dict[str, str]] = {}

        for page in self.db.get_all_pages():
            if page.status_code != 200 or not page.hreflang_json:
                continue

            try:
                hreflangs = json.loads(page.hreflang_json)
                if not hreflangs:
                    continue

                page_langs = {}
                for item in hreflangs:
                    lang = item.get('hreflang', '')
                    href = normalize_url(item.get('href', ''))

                    if lang:
                        self.report.languages_found.add(lang)
                        page_langs[lang] = href

                        # Validate language code
                        if not validate_hreflang_code(lang):
                            self.report.invalid_hreflang_codes.append((page.url, lang))

                hreflang_map[page.url] = page_langs

            except json.JSONDecodeError:
                pass

        # Check reciprocity
        for url, langs in hreflang_map.items():
            for lang, href in langs.items():
                if lang == 'x-default':
                    # x-default should not point to itself
                    if href == url:
                        self.report.x_default_issues.append({
                            'url': url,
                            'issue': 'x-default punta alla stessa pagina',
                            'suggestion': 'x-default dovrebbe puntare a una pagina di selezione lingua'
                        })
                    continue

                # Check if target has hreflang back to source
                if href in hreflang_map:
                    target_langs = hreflang_map[href]

                    # Find language of source page
                    source_lang = None
                    for src_lang, src_href in langs.items():
                        if src_href == url:
                            source_lang = src_lang
                            break

                    if source_lang:
                        # Check reciprocity
                        if source_lang not in target_langs or target_langs[source_lang] != url:
                            self.report.non_reciprocal_hreflang.append({
                                'source_url': url,
                                'source_lang': source_lang,
                                'target_url': href,
                                'target_lang': lang,
                                'issue': f'Manca hreflang reciproco da {href} verso {url}'
                            })
                else:
                    # Target page not in map (not crawled or no hreflang)
                    self.report.hreflang_issues.append(HreflangIssue(
                        url=url,
                        issue_type='missing_target',
                        description=f'La pagina target ({href}) non ha hreflang',
                        affected_languages=[lang]
                    ))

    def _analyze_navigation(self):
        """Analyze navigation and menu structure."""
        # Find homepage and extract menu links
        homepage = None
        for page in self.db.get_all_pages():
            parsed = urlparse(page.url)
            if parsed.path in ('/', ''):
                homepage = page
                break

        if not homepage or not homepage.internal_links_json:
            return

        try:
            menu_candidates = json.loads(homepage.internal_links_json)

            # Menu links are typically in nav elements, but we can approximate
            # by looking at links that appear on homepage
            menu_urls = set()
            for link in menu_candidates:
                link_url = normalize_url(link.get('url', ''))
                menu_urls.add(link_url)
                self.report.menu_links.append({
                    'url': link_url,
                    'anchor': link.get('anchor_text', '')
                })

            # Find pages not linked from homepage
            for page in self.db.get_all_pages():
                if page.status_code == 200:
                    normalized = normalize_url(page.url)
                    if normalized not in menu_urls and normalized != normalize_url(homepage.url):
                        # Check if it's linked from anywhere on homepage
                        depth = page.depth
                        if depth > 2:  # Not directly linked from homepage
                            self.report.pages_not_in_menu.append(page.url)

        except json.JSONDecodeError:
            pass

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of architecture analysis.

        Returns:
            Dictionary with summary data
        """
        return {
            'total_pages': self.report.total_pages,
            'depth_distribution': self.report.depth_distribution,
            'deep_pages_count': len(self.report.deep_pages),
            'orphan_pages_count': len(self.report.orphan_pages),
            'sections': len(self.report.site_sections),
            'url_issues': {
                'underscore': self.report.urls_with_underscore,
                'uppercase': self.report.urls_with_uppercase,
                'double_slash': self.report.urls_with_double_slash,
                'with_parameters': self.report.urls_with_parameters
            },
            'canonical_issues': {
                # Missing canonical (every page should have one, at least self-referencing)
                'missing': len(self.report.pages_without_canonical),
                'missing_list': self.report.pages_without_canonical[:20],

                # Mismatches (canonical different from URL)
                'mismatches': len(self.report.canonical_mismatches),
                'mismatches_list': [
                    {'url': url, 'canonical': canonical}
                    for url, canonical in self.report.canonical_mismatches[:20]
                ],

                # Critical errors (per Google guidelines)
                'pointing_to_404': len(self.report.canonical_to_404),
                'pointing_to_404_list': [
                    {'url': url, 'canonical': canonical}
                    for url, canonical in self.report.canonical_to_404[:10]
                ],
                'pointing_to_redirect': len(self.report.canonical_to_redirect),
                'pointing_to_redirect_list': [
                    {'url': url, 'canonical': canonical, 'redirect_code': code}
                    for url, canonical, code in self.report.canonical_to_redirect[:10]
                ],

                # Best practice violations
                'relative_urls': len(self.report.canonical_relative_urls),
                'relative_urls_list': [
                    {'url': url, 'canonical': canonical}
                    for url, canonical in self.report.canonical_relative_urls[:10]
                ],
                'http_on_https': len(self.report.canonical_http_on_https),
                'http_on_https_list': [
                    {'url': url, 'canonical': canonical}
                    for url, canonical in self.report.canonical_http_on_https[:10]
                ],
                'not_in_sitemap': len(self.report.canonical_not_in_sitemap),

                # Classification
                'intentional_count': len(self.report.canonical_intentional),
                'intentional_list': self.report.canonical_intentional[:10],
                'errors_count': len(self.report.canonical_errors),
                'errors_list': self.report.canonical_errors[:15],
            },
            'deep_pages': self.report.deep_pages[:20],  # List of deep page URLs
            'orphan_pages': self.report.orphan_pages[:20],  # List of orphan page URLs
            'hreflang': {
                'languages': list(self.report.languages_found),
                'non_reciprocal': len(self.report.non_reciprocal_hreflang),
                'non_reciprocal_list': self.report.non_reciprocal_hreflang[:10],
                'invalid_codes': len(self.report.invalid_hreflang_codes),
                'invalid_codes_list': self.report.invalid_hreflang_codes[:10],
                'x_default_issues': len(self.report.x_default_issues)
            }
        }
