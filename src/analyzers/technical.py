"""Technical SEO analyzer for performance, robots, sitemap, HTTPS, errors."""

import json
import re
import ssl
import socket
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse
from collections import defaultdict

from ..database import CrawlDatabase, PageData
from ..utils.helpers import get_status_category, format_milliseconds


@dataclass
class RedirectChain:
    """Redirect chain information."""
    start_url: str
    final_url: str
    chain: List[str]
    hops: int
    is_loop: bool = False


@dataclass
class SitemapIssue:
    """Issue found with sitemap."""
    url: str
    issue_type: str
    description: str


@dataclass
class PerformanceIssue:
    """Performance issue found."""
    url: str
    load_time_ms: int
    issue_type: str
    description: str


@dataclass
class TechnicalReport:
    """Complete technical SEO analysis report."""
    # HTTP Status
    status_distribution: Dict[int, int] = field(default_factory=dict)
    pages_200: int = 0
    pages_301: int = 0
    pages_302: int = 0
    pages_404: int = 0
    pages_500: int = 0
    error_pages: List[Tuple[str, int]] = field(default_factory=list)

    # Redirects
    redirect_chains: List[RedirectChain] = field(default_factory=list)
    redirect_loops: List[str] = field(default_factory=list)
    internal_links_to_redirects: List[Tuple[str, str]] = field(default_factory=list)  # (source, redirect_url)
    internal_links_to_404: List[Tuple[str, str]] = field(default_factory=list)

    # Robots.txt
    robots_txt_found: bool = False
    robots_txt_content: Optional[str] = None
    robots_blocked_resources: List[str] = field(default_factory=list)
    robots_sitemap_declared: bool = False
    robots_issues: List[str] = field(default_factory=list)

    # Sitemap
    sitemap_found: bool = False
    sitemap_urls_count: int = 0
    sitemap_issues: List[SitemapIssue] = field(default_factory=list)
    urls_in_sitemap_not_crawled: List[str] = field(default_factory=list)
    urls_crawled_not_in_sitemap: List[str] = field(default_factory=list)
    sitemap_urls_with_errors: List[Tuple[str, int]] = field(default_factory=list)

    # HTTPS
    uses_https: bool = False
    ssl_valid: bool = False
    ssl_expiry: Optional[str] = None
    ssl_issuer: Optional[str] = None
    mixed_content: List[Tuple[str, str]] = field(default_factory=list)  # (page_url, resource_url)
    http_links: List[Tuple[str, str]] = field(default_factory=list)  # internal links to http

    # Performance
    avg_load_time_ms: int = 0
    slow_pages: List[Tuple[str, int]] = field(default_factory=list)  # (url, ms)
    performance_issues: List[PerformanceIssue] = field(default_factory=list)

    # Robots directives (noindex, nofollow)
    noindex_pages: List[str] = field(default_factory=list)
    nofollow_pages: List[str] = field(default_factory=list)

    # Internal linking (based on AIOSEO best practices)
    orphan_pages: List[str] = field(default_factory=list)
    pages_with_many_links: List[Tuple[str, int]] = field(default_factory=list)  # url, outgoing_count
    pages_with_few_incoming: List[Tuple[str, int]] = field(default_factory=list)  # url, incoming_count (1-2 links)
    # Link equity distribution
    incoming_links_distribution: Dict[str, int] = field(default_factory=dict)  # url -> incoming count
    avg_incoming_links: float = 0.0
    max_incoming_links: int = 0
    top_linked_pages: List[Tuple[str, int]] = field(default_factory=list)  # Most linked pages (hub candidates)
    # Outgoing links
    avg_outgoing_links: float = 0.0
    pages_with_no_outgoing: List[str] = field(default_factory=list)  # Dead-end pages
    # Anchor text analysis
    generic_anchors_count: int = 0  # "click here", "read more", etc.
    generic_anchors_list: List[Dict] = field(default_factory=list)  # {url, anchor, target}


class TechnicalAnalyzer:
    """Analyzer for technical SEO aspects."""

    SLOW_PAGE_THRESHOLD_MS = 3000  # 3 seconds
    MAX_LINKS_PER_PAGE = 100

    def __init__(self, db: CrawlDatabase, base_url: str):
        """Initialize analyzer.

        Args:
            db: Database with crawl data
            base_url: Base URL of the site being analyzed
        """
        self.db = db
        self.base_url = base_url
        parsed = urlparse(base_url)
        self.domain = parsed.netloc
        self.report = TechnicalReport()

    def analyze(self) -> TechnicalReport:
        """Run complete technical analysis.

        Returns:
            TechnicalReport with all findings
        """
        self._analyze_status_codes()
        self._analyze_redirects()
        self._analyze_robots_txt()
        self._analyze_sitemap()
        self._analyze_https()
        self._analyze_performance()
        self._analyze_robots_directives()
        self._analyze_internal_linking()

        return self.report

    def _analyze_status_codes(self):
        """Analyze HTTP status code distribution."""
        status_counts = defaultdict(int)

        for page in self.db.get_all_pages():
            status = page.status_code or 0
            status_counts[status] += 1

            if status == 200:
                self.report.pages_200 += 1
            elif status == 301:
                self.report.pages_301 += 1
            elif status == 302:
                self.report.pages_302 += 1
            elif status == 404:
                self.report.pages_404 += 1
                self.report.error_pages.append((page.url, status))
            elif status >= 500:
                self.report.pages_500 += 1
                self.report.error_pages.append((page.url, status))
            elif status >= 400:
                self.report.error_pages.append((page.url, status))

        self.report.status_distribution = dict(status_counts)

    def _analyze_redirects(self):
        """Analyze redirect chains and loops."""
        # Build redirect map
        redirect_map: Dict[str, str] = {}
        for page in self.db.get_all_pages():
            if page.redirect_url:
                redirect_map[page.url] = page.redirect_url

        # Find chains
        for start_url, redirect_url in redirect_map.items():
            chain = [start_url]
            current = redirect_url
            visited = {start_url}

            while current in redirect_map:
                if current in visited:
                    # Loop detected
                    chain.append(current)
                    self.report.redirect_chains.append(RedirectChain(
                        start_url=start_url,
                        final_url=current,
                        chain=chain,
                        hops=len(chain) - 1,
                        is_loop=True
                    ))
                    self.report.redirect_loops.append(start_url)
                    break

                chain.append(current)
                visited.add(current)
                current = redirect_map[current]
            else:
                chain.append(current)
                if len(chain) > 2:  # More than one redirect
                    self.report.redirect_chains.append(RedirectChain(
                        start_url=start_url,
                        final_url=current,
                        chain=chain,
                        hops=len(chain) - 1,
                        is_loop=False
                    ))

        # Find internal links pointing to redirects or 404s
        status_map = {page.url: page.status_code for page in self.db.get_all_pages()}

        for page in self.db.get_all_pages():
            if page.status_code != 200 or not page.internal_links_json:
                continue

            try:
                links = json.loads(page.internal_links_json)
                for link in links:
                    target_url = link.get('url', '')
                    if target_url in status_map:
                        target_status = status_map[target_url]
                        if target_status in (301, 302, 307, 308):
                            self.report.internal_links_to_redirects.append((page.url, target_url))
                        elif target_status == 404:
                            self.report.internal_links_to_404.append((page.url, target_url))
            except json.JSONDecodeError:
                pass

    def _analyze_robots_txt(self):
        """Analyze robots.txt content."""
        robots_content = self.db.get_robots_txt()

        if not robots_content:
            self.report.robots_txt_found = False
            return

        self.report.robots_txt_found = True
        self.report.robots_txt_content = robots_content

        # Parse robots.txt
        current_ua = None
        for line in robots_content.splitlines():
            line = line.strip()

            # Skip comments
            if line.startswith('#') or not line:
                continue

            # Check for sitemap
            if line.lower().startswith('sitemap:'):
                self.report.robots_sitemap_declared = True

            # Check for user-agent
            if line.lower().startswith('user-agent:'):
                current_ua = line.split(':', 1)[1].strip()

            # Check for disallow
            if line.lower().startswith('disallow:'):
                path = line.split(':', 1)[1].strip()
                if path == '/':
                    self.report.robots_issues.append(
                        f"Disallow: / blocca tutto il sito per user-agent: {current_ua}"
                    )
                elif path:
                    # Check if blocking important resources
                    if any(ext in path.lower() for ext in ['.css', '.js']):
                        self.report.robots_blocked_resources.append(path)
                        self.report.robots_issues.append(
                            f"Blocco di risorse CSS/JS: {path}"
                        )

    def _analyze_sitemap(self):
        """Analyze sitemap against crawled pages."""
        sitemap_urls = self.db.get_sitemap_urls()

        if not sitemap_urls:
            self.report.sitemap_found = False
            return

        self.report.sitemap_found = True
        self.report.sitemap_urls_count = len(sitemap_urls)

        sitemap_url_set = {item['url'] for item in sitemap_urls}
        crawled_urls = {page.url for page in self.db.get_all_pages() if page.status_code == 200}

        # URLs in sitemap but not crawled (might be 404, redirect, etc.)
        for url in sitemap_url_set - crawled_urls:
            page = self.db.get_page(url)
            if page:
                if page.status_code != 200:
                    self.report.sitemap_urls_with_errors.append((url, page.status_code))
                    self.report.sitemap_issues.append(SitemapIssue(
                        url=url,
                        issue_type='error_status',
                        description=f'URL in sitemap restituisce status {page.status_code}'
                    ))
            else:
                self.report.urls_in_sitemap_not_crawled.append(url)

        # URLs crawled but not in sitemap
        for url in crawled_urls - sitemap_url_set:
            # Skip non-indexable pages
            page = self.db.get_page(url)
            if page and page.robots_directives:
                if 'noindex' in page.robots_directives.lower():
                    continue
            self.report.urls_crawled_not_in_sitemap.append(url)

    def _analyze_https(self):
        """Analyze HTTPS and SSL."""
        parsed = urlparse(self.base_url)
        self.report.uses_https = parsed.scheme == 'https'

        # Check SSL certificate
        if self.report.uses_https:
            try:
                context = ssl.create_default_context()
                with socket.create_connection((self.domain, 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=self.domain) as ssock:
                        cert = ssock.getpeercert()
                        self.report.ssl_valid = True

                        # Get expiry
                        not_after = cert.get('notAfter')
                        if not_after:
                            self.report.ssl_expiry = not_after

                        # Get issuer
                        issuer = cert.get('issuer')
                        if issuer:
                            for item in issuer:
                                if item[0][0] == 'organizationName':
                                    self.report.ssl_issuer = item[0][1]
                                    break

            except (ssl.SSLError, socket.error) as e:
                self.report.ssl_valid = False

        # Check for mixed content and HTTP links
        for page in self.db.get_all_pages():
            if page.status_code != 200:
                continue

            # Check images for HTTP
            if page.images_json:
                try:
                    images = json.loads(page.images_json)
                    for img in images:
                        src = img.get('src', '')
                        if src.startswith('http://'):
                            self.report.mixed_content.append((page.url, src))
                except json.JSONDecodeError:
                    pass

            # Check internal links for HTTP
            if page.internal_links_json:
                try:
                    links = json.loads(page.internal_links_json)
                    for link in links:
                        url = link.get('url', '')
                        if url.startswith('http://'):
                            self.report.http_links.append((page.url, url))
                except json.JSONDecodeError:
                    pass

    def _analyze_performance(self):
        """Analyze page load times."""
        load_times = []

        for page in self.db.get_all_pages():
            if page.status_code != 200 or not page.load_time_ms:
                continue

            load_times.append(page.load_time_ms)

            if page.load_time_ms > self.SLOW_PAGE_THRESHOLD_MS:
                self.report.slow_pages.append((page.url, page.load_time_ms))
                self.report.performance_issues.append(PerformanceIssue(
                    url=page.url,
                    load_time_ms=page.load_time_ms,
                    issue_type='slow_load',
                    description=f'Tempo di caricamento elevato: {format_milliseconds(page.load_time_ms)}'
                ))

        if load_times:
            self.report.avg_load_time_ms = int(sum(load_times) / len(load_times))

    def _analyze_robots_directives(self):
        """Analyze robots meta directives (noindex, nofollow)."""
        for page in self.db.get_all_pages():
            if page.status_code != 200 or not page.robots_directives:
                continue

            directives = page.robots_directives.lower()
            if 'noindex' in directives:
                self.report.noindex_pages.append(page.url)
            if 'nofollow' in directives:
                self.report.nofollow_pages.append(page.url)

    def _analyze_internal_linking(self):
        """Analyze internal linking structure based on AIOSEO best practices.

        Analyzes:
        - Orphan pages (no incoming links)
        - Pages with few incoming links (low link equity)
        - Pages with too many outgoing links (link dilution)
        - Dead-end pages (no outgoing links)
        - Link equity distribution
        - Generic anchor text usage
        - Top linked pages (potential hub pages)

        Reference: https://aioseo.com/internal-linking-best-practices/
        """
        # Generic anchor patterns to detect
        GENERIC_ANCHORS = {
            'click here', 'clicca qui', 'here', 'qui', 'read more', 'leggi tutto',
            'learn more', 'scopri di più', 'more', 'altro', 'link', 'this', 'questo',
            'page', 'pagina', 'article', 'articolo', 'post', 'continue', 'continua',
            'details', 'dettagli', 'info', 'website', 'sito', 'vai', 'go'
        }

        # Count incoming/outgoing links for each page
        incoming_links = defaultdict(int)
        outgoing_links = defaultdict(int)
        total_outgoing = 0
        pages_with_links = 0

        for page in self.db.get_all_pages():
            if page.status_code != 200 or not page.internal_links_json:
                continue

            try:
                links = json.loads(page.internal_links_json)
                link_count = len(links)
                outgoing_links[page.url] = link_count
                total_outgoing += link_count
                pages_with_links += 1

                for link in links:
                    target_url = link.get('url', '')
                    anchor = link.get('anchor', '').strip().lower()

                    incoming_links[target_url] += 1

                    # Check for generic anchor text
                    if anchor and anchor in GENERIC_ANCHORS:
                        self.report.generic_anchors_count += 1
                        if len(self.report.generic_anchors_list) < 20:
                            self.report.generic_anchors_list.append({
                                'source': page.url,
                                'anchor': link.get('anchor', ''),
                                'target': target_url
                            })

                # Check for too many outgoing links (link dilution)
                if link_count > self.MAX_LINKS_PER_PAGE:
                    self.report.pages_with_many_links.append((page.url, link_count))

                # Check for dead-end pages (no outgoing links)
                if link_count == 0:
                    self.report.pages_with_no_outgoing.append(page.url)

            except json.JSONDecodeError:
                pass

        # Calculate averages
        if pages_with_links > 0:
            self.report.avg_outgoing_links = round(total_outgoing / pages_with_links, 1)

        # Store incoming links distribution
        self.report.incoming_links_distribution = dict(incoming_links)

        if incoming_links:
            valid_incoming = [c for c in incoming_links.values() if c > 0]
            if valid_incoming:
                self.report.avg_incoming_links = round(sum(valid_incoming) / len(valid_incoming), 1)
                self.report.max_incoming_links = max(valid_incoming)

        # Find top linked pages (potential hub/pillar pages)
        sorted_by_incoming = sorted(incoming_links.items(), key=lambda x: x[1], reverse=True)
        self.report.top_linked_pages = sorted_by_incoming[:10]

        # Analyze each page
        for page in self.db.get_all_pages():
            if page.status_code != 200:
                continue

            page_url = page.url
            incoming_count = incoming_links.get(page_url, 0)

            # Skip homepage for orphan analysis
            parsed = urlparse(page_url)
            is_homepage = parsed.path in ('/', '')

            if not is_homepage:
                if incoming_count == 0:
                    # Orphan page - no incoming links at all
                    self.report.orphan_pages.append(page_url)
                elif incoming_count <= 2:
                    # Low link equity - only 1-2 incoming links
                    self.report.pages_with_few_incoming.append((page_url, incoming_count))

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of technical analysis.

        Returns:
            Dictionary with summary data including example lists for AI analysis
        """
        # Prepare slow pages list with timing
        slow_pages_list = [
            {'url': url, 'time_ms': time_ms}
            for url, time_ms in self.report.slow_pages[:15]
        ] if self.report.slow_pages else []

        # Prepare internal links to 404
        internal_to_404_list = [
            {'source': src, 'target': tgt}
            for src, tgt in self.report.internal_links_to_404[:15]
        ] if self.report.internal_links_to_404 else []

        # Prepare redirect chains
        redirect_chains_list = [
            {'start': chain[0], 'hops': len(chain) - 1, 'chain': chain[:5]}
            for chain in self.report.redirect_chains[:10]
        ] if self.report.redirect_chains else []

        return {
            'status_codes': {
                'success_200': self.report.pages_200,
                'redirect_301': self.report.pages_301,
                'redirect_302': self.report.pages_302,
                'not_found_404': self.report.pages_404,
                'server_error_5xx': self.report.pages_500
            },
            'redirects': {
                'chains': len(self.report.redirect_chains),
                'redirect_chains_list': redirect_chains_list,
                'loops': len(self.report.redirect_loops),
                'redirect_loops_list': self.report.redirect_loops[:5],
                'internal_to_redirects': len(self.report.internal_links_to_redirects),
                'internal_to_404': len(self.report.internal_links_to_404),
                'internal_to_404_list': internal_to_404_list
            },
            'robots_txt': {
                'found': self.report.robots_txt_found,
                'sitemap_declared': self.report.robots_sitemap_declared,
                'issues': len(self.report.robots_issues),
                'issues_list': self.report.robots_issues[:5]
            },
            'sitemap': {
                'found': self.report.sitemap_found,
                'urls_count': self.report.sitemap_urls_count,
                'urls_with_errors': len(self.report.sitemap_urls_with_errors),
                'urls_with_errors_list': self.report.sitemap_urls_with_errors[:10],
                'missing_from_sitemap': len(self.report.urls_crawled_not_in_sitemap),
                'not_in_sitemap_list': self.report.urls_crawled_not_in_sitemap[:15]
            },
            'https': {
                'uses_https': self.report.uses_https,
                'ssl_valid': self.report.ssl_valid,
                'mixed_content': len(self.report.mixed_content),
                'mixed_content_list': self.report.mixed_content[:10],
                'http_links': len(self.report.http_links),
                'http_links_list': self.report.http_links[:10]
            },
            'performance': {
                'avg_load_time_ms': self.report.avg_load_time_ms,
                'slow_pages': len(self.report.slow_pages),
                'slow_pages_list': slow_pages_list
            },
            'robots_directives': {
                'noindex': len(self.report.noindex_pages),
                'noindex_list': self.report.noindex_pages[:10],
                'nofollow': len(self.report.nofollow_pages),
                'nofollow_list': self.report.nofollow_pages[:10]
            },
            'internal_linking': {
                # Orphan pages (no incoming links - critical for SEO)
                'orphan_pages': len(self.report.orphan_pages),
                'orphan_pages_list': self.report.orphan_pages[:15],

                # Pages with low link equity (1-2 incoming links)
                'pages_with_few_incoming': len(self.report.pages_with_few_incoming),
                'pages_with_few_incoming_list': [
                    {'url': url, 'incoming': count}
                    for url, count in self.report.pages_with_few_incoming[:15]
                ],

                # Pages with too many outgoing links (link dilution)
                'pages_with_many_links': len(self.report.pages_with_many_links),
                'pages_with_many_links_list': [
                    {'url': url, 'outgoing': count}
                    for url, count in self.report.pages_with_many_links[:10]
                ],

                # Dead-end pages (no outgoing links)
                'dead_end_pages': len(self.report.pages_with_no_outgoing),
                'dead_end_pages_list': self.report.pages_with_no_outgoing[:10],

                # Link equity distribution
                'avg_incoming_links': self.report.avg_incoming_links,
                'avg_outgoing_links': self.report.avg_outgoing_links,
                'max_incoming_links': self.report.max_incoming_links,

                # Top linked pages (potential pillar/hub pages)
                'top_linked_pages': [
                    {'url': url, 'incoming': count}
                    for url, count in self.report.top_linked_pages[:10]
                ],

                # Generic anchor text (bad for SEO)
                'generic_anchors': self.report.generic_anchors_count,
                'generic_anchors_list': self.report.generic_anchors_list[:15],
            }
        }
