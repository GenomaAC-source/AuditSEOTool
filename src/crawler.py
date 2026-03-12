"""Asynchronous web crawler for SEO auditing."""

import asyncio
import hashlib
import json
import re
import time
from datetime import datetime
from typing import Optional, List, Set, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .database import CrawlDatabase, PageData

console = Console()


class RobotsParser:
    """Parser for robots.txt with caching."""

    def __init__(self):
        self.parsers: Dict[str, RobotFileParser] = {}

    async def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """Check if URL can be fetched according to robots.txt."""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{base_url}/robots.txt"

        if base_url not in self.parsers:
            parser = RobotFileParser()
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(robots_url)
                    if response.status_code == 200:
                        parser.parse(response.text.splitlines())
                    else:
                        # No robots.txt or error, allow all
                        parser.allow_all = True
            except Exception:
                parser.allow_all = True

            self.parsers[base_url] = parser

        parser = self.parsers[base_url]
        if hasattr(parser, 'allow_all') and parser.allow_all:
            return True
        return parser.can_fetch(user_agent, url)


class AsyncCrawler:
    """Asynchronous crawler for SEO auditing."""

    def __init__(
        self,
        start_url: str,
        db: CrawlDatabase,
        max_pages: Optional[int] = None,
        concurrency: int = 10,
        delay_ms: int = 100,
        respect_robots: bool = True,
        user_agent: str = "AuditSEOBot/1.0 (+https://github.com/auditseo)"
    ):
        """Initialize crawler.

        Args:
            start_url: Starting URL for crawl
            db: Database instance for storing results
            max_pages: Maximum pages to crawl (None for unlimited)
            concurrency: Number of concurrent requests
            delay_ms: Delay between requests in milliseconds
            respect_robots: Whether to respect robots.txt
            user_agent: User agent string
        """
        self.start_url = self._normalize_url(start_url)
        self.db = db
        self.max_pages = max_pages
        self.concurrency = concurrency
        self.delay_ms = delay_ms
        self.respect_robots = respect_robots
        self.user_agent = user_agent

        parsed = urlparse(self.start_url)
        self.base_domain = parsed.netloc
        self.base_scheme = parsed.scheme

        self.robots_parser = RobotsParser()
        self.crawled_count = 0
        self.semaphore = asyncio.Semaphore(concurrency)

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistent comparison."""
        parsed = urlparse(url)

        # Ensure scheme
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)

        # Remove fragment
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path.rstrip('/') if parsed.path != '/' else '/',
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))

        return normalized

    def _is_internal_url(self, url: str) -> bool:
        """Check if URL is internal to the base domain."""
        parsed = urlparse(url)
        return parsed.netloc.lower() == self.base_domain.lower()

    def _should_crawl(self, url: str) -> bool:
        """Determine if URL should be crawled."""
        parsed = urlparse(url)

        # Must be same domain
        if not self._is_internal_url(url):
            return False

        # Must be http(s)
        if parsed.scheme not in ('http', 'https'):
            return False

        # Skip common non-page extensions
        skip_extensions = {
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
            '.css', '.js', '.ico', '.woff', '.woff2', '.ttf', '.eot',
            '.mp4', '.mp3', '.avi', '.mov', '.zip', '.rar', '.tar',
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
        }
        path_lower = parsed.path.lower()
        for ext in skip_extensions:
            if path_lower.endswith(ext):
                return False

        return True

    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract main text content from page."""
        # Remove script, style, nav, footer, header
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
            tag.decompose()

        # Try to find main content
        main_content = soup.find('main') or soup.find('article') or soup.find(id='content') or soup.find(class_='content')

        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
        else:
            # Fallback to body
            body = soup.find('body')
            text = body.get_text(separator=' ', strip=True) if body else ''

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _is_navigation_link(self, a_tag) -> bool:
        """Check if a link is inside navigation elements (menu, header, footer).

        Navigation links are not considered for strategic linking analysis
        because they appear on every page and don't represent contextual linking.
        """
        # Navigation element names
        nav_elements = {'nav', 'header', 'footer'}

        # Common navigation class/id patterns
        nav_patterns = [
            'nav', 'menu', 'header', 'footer', 'sidebar',
            'navigation', 'top-bar', 'topbar', 'bottom-bar',
            'main-nav', 'main-menu', 'site-header', 'site-footer',
            'navbar', 'footerbar', 'breadcrumb', 'pagination'
        ]

        # Check parent elements
        for parent in a_tag.parents:
            if parent.name is None:
                continue

            # Check element name
            if parent.name.lower() in nav_elements:
                return True

            # Check class attribute
            classes = parent.get('class', [])
            if classes:
                class_str = ' '.join(classes).lower()
                for pattern in nav_patterns:
                    if pattern in class_str:
                        return True

            # Check id attribute
            elem_id = parent.get('id', '')
            if elem_id:
                id_lower = elem_id.lower()
                for pattern in nav_patterns:
                    if pattern in id_lower:
                        return True

            # Check role attribute
            role = parent.get('role', '').lower()
            if role in ('navigation', 'banner', 'contentinfo'):
                return True

        return False

    def _extract_links(self, soup: BeautifulSoup, page_url: str) -> Tuple[List[Dict], List[Dict]]:
        """Extract internal and external links from page.

        Links are classified as 'navigation' or 'content' based on their location.
        Navigation links (in nav, header, footer, menus) are marked separately
        because they don't represent strategic internal linking.
        """
        internal_links = []
        external_links = []

        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '').strip()
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue

            # Resolve relative URLs
            full_url = urljoin(page_url, href)
            full_url = self._normalize_url(full_url)

            anchor_text = a_tag.get_text(strip=True)[:200]  # Limit anchor text length
            rel = a_tag.get('rel', [])
            nofollow = 'nofollow' in rel if isinstance(rel, list) else 'nofollow' in str(rel)

            # Determine if this is a navigation or content link
            is_nav = self._is_navigation_link(a_tag)

            link_data = {
                'url': full_url,
                'anchor_text': anchor_text,
                'nofollow': nofollow,
                'link_type': 'navigation' if is_nav else 'content'
            }

            if self._is_internal_url(full_url):
                internal_links.append(link_data)
            else:
                external_links.append(link_data)

        return internal_links, external_links

    def _extract_images(self, soup: BeautifulSoup, page_url: str) -> List[Dict]:
        """Extract images with alt text."""
        images = []
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src:
                full_src = urljoin(page_url, src)
                images.append({
                    'src': full_src,
                    'alt': img.get('alt', ''),
                    'title': img.get('title', ''),
                    'loading': img.get('loading', '')
                })
        return images

    def _extract_headings(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract all headings."""
        headings = {}
        for level in range(1, 7):
            tag = f'h{level}'
            headings[tag] = [h.get_text(strip=True) for h in soup.find_all(tag)]
        return headings

    def _extract_hreflang(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract hreflang tags."""
        hreflang_tags = []
        for link in soup.find_all('link', rel='alternate'):
            hreflang = link.get('hreflang')
            if hreflang:
                hreflang_tags.append({
                    'hreflang': hreflang,
                    'href': link.get('href', '')
                })
        return hreflang_tags

    def _extract_structured_data(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract JSON-LD structured data."""
        structured_data = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                structured_data.append(data)
            except (json.JSONDecodeError, TypeError):
                pass
        return structured_data

    def _extract_robots_directives(self, soup: BeautifulSoup) -> str:
        """Extract robots meta directives."""
        meta_robots = soup.find('meta', attrs={'name': re.compile(r'^robots$', re.I)})
        if meta_robots:
            return meta_robots.get('content', '')
        return ''

    def _compute_content_hash(self, text: str) -> str:
        """Compute hash of text content for duplicate detection."""
        # Normalize text for comparison
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        return hashlib.md5(normalized.encode()).hexdigest()

    async def _fetch_page(self, url: str, client: httpx.AsyncClient) -> Tuple[Optional[str], int, Optional[str], List[str], int]:
        """Fetch a page and return (html, status_code, redirect_url, redirect_chain, load_time_ms).

        Note: If redirects occurred, status_code will be the status of the ORIGINAL request (e.g., 301),
        not the final destination. This prevents redirect pages from being analyzed as 200 OK pages.
        """
        redirect_chain = []
        final_url = url
        start_time = time.time()

        try:
            response = await client.get(url, follow_redirects=True)
            load_time_ms = int((time.time() - start_time) * 1000)

            # Determine actual status code
            # If there were redirects, use the status of the FIRST redirect, not the final response
            if response.history:
                redirect_chain = [str(r.url) for r in response.history]
                final_url = str(response.url)
                # Use the status code of the ORIGINAL request (first redirect)
                actual_status = response.history[0].status_code
            else:
                # No redirects, use the response status
                actual_status = response.status_code

            content_type = response.headers.get('content-type', '')

            # Only return HTML content if this is NOT a redirect page
            # Redirect pages (301, 302, etc.) should not have their content analyzed
            if 'text/html' in content_type and not response.history:
                return response.text, actual_status, final_url if redirect_chain else None, redirect_chain, load_time_ms
            else:
                # For redirects or non-HTML, don't return content
                return None, actual_status, final_url if redirect_chain else None, redirect_chain, load_time_ms

        except httpx.TimeoutException:
            return None, 0, None, [], 0
        except Exception as e:
            return None, 0, None, [], 0

    async def _crawl_page(self, url: str, depth: int, client: httpx.AsyncClient) -> Optional[PageData]:
        """Crawl a single page."""
        async with self.semaphore:
            # Check robots.txt
            if self.respect_robots:
                if not await self.robots_parser.can_fetch(url, self.user_agent):
                    return None

            # Rate limiting
            if self.delay_ms > 0:
                await asyncio.sleep(self.delay_ms / 1000)

            html, status_code, redirect_url, redirect_chain, load_time_ms = await self._fetch_page(url, client)

            page_data = PageData(
                url=url,
                status_code=status_code,
                depth=depth,
                crawled_at=datetime.now().isoformat(),
                redirect_url=redirect_url,
                redirect_chain_json=json.dumps(redirect_chain) if redirect_chain else None,
                load_time_ms=load_time_ms
            )

            if html and status_code == 200:
                soup = BeautifulSoup(html, 'lxml')

                # Extract metadata
                page_data.html = html
                page_data.title = soup.title.string.strip() if soup.title and soup.title.string else None

                # Meta description
                meta_desc = soup.find('meta', attrs={'name': re.compile(r'^description$', re.I)})
                page_data.meta_description = meta_desc.get('content', '').strip() if meta_desc else None

                # Meta keywords
                meta_kw = soup.find('meta', attrs={'name': re.compile(r'^keywords$', re.I)})
                page_data.meta_keywords = meta_kw.get('content', '').strip() if meta_kw else None

                # Canonical
                canonical = soup.find('link', rel='canonical')
                page_data.canonical = canonical.get('href', '').strip() if canonical else None

                # H1
                h1_tags = soup.find_all('h1')
                page_data.h1_count = len(h1_tags)
                page_data.h1 = h1_tags[0].get_text(strip=True) if h1_tags else None

                # All headings
                headings = self._extract_headings(soup)
                page_data.headings_json = json.dumps(headings)

                # Hreflang
                hreflang = self._extract_hreflang(soup)
                page_data.hreflang_json = json.dumps(hreflang) if hreflang else None

                # Images
                images = self._extract_images(soup, url)
                page_data.images_json = json.dumps(images)

                # Links
                internal_links, external_links = self._extract_links(soup, url)
                page_data.internal_links_json = json.dumps(internal_links)
                page_data.external_links_json = json.dumps(external_links)

                # Structured data
                structured_data = self._extract_structured_data(soup)
                page_data.structured_data_json = json.dumps(structured_data) if structured_data else None

                # Text content
                text_content = self._extract_text_content(soup)
                page_data.text_content = text_content
                page_data.word_count = len(text_content.split())
                page_data.content_hash = self._compute_content_hash(text_content)

                # Robots directives
                page_data.robots_directives = self._extract_robots_directives(soup)

                # Save links for graph analysis
                for link in internal_links:
                    self.db.save_link(
                        source_url=url,
                        target_url=link['url'],
                        anchor_text=link['anchor_text'],
                        is_internal=True,
                        nofollow=link['nofollow']
                    )

                    # Add to queue if should crawl
                    if self._should_crawl(link['url']) and not self.db.is_url_crawled(link['url']):
                        self.db.add_to_queue(link['url'], source_url=url, depth=depth + 1)

                for link in external_links:
                    self.db.save_link(
                        source_url=url,
                        target_url=link['url'],
                        anchor_text=link['anchor_text'],
                        is_internal=False,
                        nofollow=link['nofollow']
                    )

            # Handle redirects: add destination URL to crawl queue if internal
            elif redirect_url and status_code in (301, 302, 303, 307, 308):
                # If redirect destination is internal and not yet crawled, add to queue
                if self._should_crawl(redirect_url) and not self.db.is_url_crawled(redirect_url):
                    self.db.add_to_queue(redirect_url, source_url=url, depth=depth)

                # Save redirect as a link for analysis
                self.db.save_link(
                    source_url=url,
                    target_url=redirect_url,
                    anchor_text=f"[Redirect {status_code}]",
                    is_internal=self._is_internal_url(redirect_url),
                    nofollow=False
                )

            return page_data

    async def _fetch_robots_txt(self, client: httpx.AsyncClient):
        """Fetch and save robots.txt."""
        robots_url = f"{self.base_scheme}://{self.base_domain}/robots.txt"
        try:
            response = await client.get(robots_url)
            if response.status_code == 200:
                self.db.save_robots_txt(response.text)
        except Exception:
            pass

    async def _fetch_sitemap(self, client: httpx.AsyncClient):
        """Fetch and parse sitemap."""
        sitemap_urls_to_try = [
            f"{self.base_scheme}://{self.base_domain}/sitemap.xml",
            f"{self.base_scheme}://{self.base_domain}/sitemap_index.xml",
        ]

        # Also check robots.txt for sitemap
        robots_content = self.db.get_robots_txt()
        if robots_content:
            for line in robots_content.splitlines():
                if line.lower().startswith('sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    if sitemap_url not in sitemap_urls_to_try:
                        sitemap_urls_to_try.insert(0, sitemap_url)

        for sitemap_url in sitemap_urls_to_try:
            try:
                response = await client.get(sitemap_url)
                if response.status_code == 200:
                    await self._parse_sitemap(response.text, client)
                    break
            except Exception:
                continue

    async def _parse_sitemap(self, content: str, client: httpx.AsyncClient):
        """Parse sitemap XML."""
        soup = BeautifulSoup(content, 'lxml-xml')

        # Check if it's a sitemap index
        sitemap_tags = soup.find_all('sitemap')
        if sitemap_tags:
            for sitemap_tag in sitemap_tags:
                loc = sitemap_tag.find('loc')
                if loc:
                    try:
                        response = await client.get(loc.text.strip())
                        if response.status_code == 200:
                            await self._parse_sitemap(response.text, client)
                    except Exception:
                        continue
        else:
            # Regular sitemap
            urls = []
            for url_tag in soup.find_all('url'):
                loc = url_tag.find('loc')
                if loc:
                    url_data = {
                        'url': loc.text.strip(),
                        'lastmod': url_tag.find('lastmod').text.strip() if url_tag.find('lastmod') else None,
                        'changefreq': url_tag.find('changefreq').text.strip() if url_tag.find('changefreq') else None,
                        'priority': float(url_tag.find('priority').text.strip()) if url_tag.find('priority') else None
                    }
                    urls.append(url_data)

            if urls:
                self.db.save_sitemap_urls(urls)

    async def crawl(self, resume: bool = False) -> Dict[str, Any]:
        """Start crawling.

        Args:
            resume: If True, continue from previous crawl state

        Returns:
            Dictionary with crawl statistics
        """
        if not resume:
            self.db.clear_all()

        crawl_id = self.db.start_crawl()

        # Add start URL to queue
        self.db.add_to_queue(self.start_url, depth=0)

        async with httpx.AsyncClient(
            timeout=30.0,
            headers={'User-Agent': self.user_agent},
            follow_redirects=True,
            http2=True
        ) as client:
            # Fetch robots.txt and sitemap first
            await self._fetch_robots_txt(client)
            await self._fetch_sitemap(client)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]Crawling...", total=self.max_pages if self.max_pages else 1000)

                while True:
                    # Check max pages
                    if self.max_pages and self.crawled_count >= self.max_pages:
                        break

                    # Get pending URLs
                    pending = self.db.get_pending_urls(limit=self.concurrency)
                    if not pending:
                        break

                    # Crawl in parallel
                    tasks = []
                    for url_data in pending:
                        if self.max_pages and self.crawled_count >= self.max_pages:
                            break
                        if not self.db.is_url_crawled(url_data['url']):
                            tasks.append(self._crawl_page(url_data['url'], url_data['depth'], client))

                    if not tasks:
                        # All pending already crawled, get more
                        for url_data in pending:
                            self.db.mark_url_crawled(url_data['url'])
                        continue

                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for url_data, result in zip(pending[:len(results)], results):
                        if isinstance(result, Exception):
                            self.db.mark_url_failed(url_data['url'])
                        elif result:
                            self.db.save_page(result)
                            self.db.mark_url_crawled(url_data['url'])
                            self.crawled_count += 1
                            progress.update(task, completed=self.crawled_count)
                        else:
                            self.db.mark_url_crawled(url_data['url'])

        self.db.complete_crawl(crawl_id)
        return self.db.get_statistics()


async def run_crawl(
    url: str,
    db: CrawlDatabase,
    max_pages: Optional[int] = None,
    concurrency: int = 10,
    delay_ms: int = 100,
    resume: bool = False
) -> Dict[str, Any]:
    """Convenience function to run crawler.

    Args:
        url: Starting URL
        db: Database instance
        max_pages: Maximum pages to crawl
        concurrency: Number of concurrent requests
        delay_ms: Delay between requests
        resume: Continue from previous state

    Returns:
        Crawl statistics
    """
    crawler = AsyncCrawler(
        start_url=url,
        db=db,
        max_pages=max_pages,
        concurrency=concurrency,
        delay_ms=delay_ms
    )
    return await crawler.crawl(resume=resume)
