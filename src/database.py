"""Database module for storing crawl data in SQLite."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Iterator
from dataclasses import dataclass, asdict
from contextlib import contextmanager


@dataclass
class PageData:
    """Data structure for a crawled page."""
    url: str
    status_code: int
    content_type: Optional[str] = None
    html: Optional[str] = None
    text_content: Optional[str] = None
    title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None
    canonical: Optional[str] = None
    h1: Optional[str] = None
    h1_count: int = 0
    headings_json: Optional[str] = None  # JSON of all headings
    hreflang_json: Optional[str] = None  # JSON of hreflang tags
    images_json: Optional[str] = None  # JSON of images with alt text
    internal_links_json: Optional[str] = None  # JSON of internal links
    external_links_json: Optional[str] = None  # JSON of external links
    structured_data_json: Optional[str] = None  # JSON of structured data
    word_count: int = 0
    load_time_ms: Optional[int] = None
    content_hash: Optional[str] = None  # For duplicate detection
    depth: int = 0  # Click depth from homepage
    crawled_at: Optional[str] = None
    redirect_url: Optional[str] = None
    redirect_chain_json: Optional[str] = None
    robots_directives: Optional[str] = None  # noindex, nofollow, etc.
    error_message: Optional[str] = None


class CrawlDatabase:
    """SQLite database for storing and managing crawl data."""

    def __init__(self, domain: str, data_dir: Path = None):
        """Initialize database for a domain.

        Args:
            domain: The domain being crawled (e.g., 'example.com')
            data_dir: Directory to store data files
        """
        self.domain = domain
        if data_dir is None:
            data_dir = Path("data")

        self.domain_dir = data_dir / domain.replace(".", "_").replace(":", "_")
        self.domain_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.domain_dir / "crawl.db"
        self.screenshots_dir = self.domain_dir / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)

        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Pages table - main storage for crawled pages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    status_code INTEGER,
                    content_type TEXT,
                    html TEXT,
                    text_content TEXT,
                    title TEXT,
                    meta_description TEXT,
                    meta_keywords TEXT,
                    canonical TEXT,
                    h1 TEXT,
                    h1_count INTEGER DEFAULT 0,
                    headings_json TEXT,
                    hreflang_json TEXT,
                    images_json TEXT,
                    internal_links_json TEXT,
                    external_links_json TEXT,
                    structured_data_json TEXT,
                    word_count INTEGER DEFAULT 0,
                    load_time_ms INTEGER,
                    content_hash TEXT,
                    depth INTEGER DEFAULT 0,
                    crawled_at TEXT,
                    redirect_url TEXT,
                    redirect_chain_json TEXT,
                    robots_directives TEXT,
                    error_message TEXT
                )
            """)

            # Queue table - URLs to be crawled
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crawl_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    source_url TEXT,
                    depth INTEGER DEFAULT 0,
                    added_at TEXT,
                    status TEXT DEFAULT 'pending'
                )
            """)

            # Links table - all internal links found
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_url TEXT NOT NULL,
                    target_url TEXT NOT NULL,
                    anchor_text TEXT,
                    is_internal INTEGER DEFAULT 1,
                    link_type TEXT,
                    nofollow INTEGER DEFAULT 0,
                    UNIQUE(source_url, target_url)
                )
            """)

            # Sitemap URLs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sitemap_urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    lastmod TEXT,
                    changefreq TEXT,
                    priority REAL
                )
            """)

            # Robots.txt content
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS robots_txt (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT,
                    fetched_at TEXT
                )
            """)

            # Crawl metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crawl_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    pages_crawled INTEGER DEFAULT 0,
                    pages_with_errors INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running'
                )
            """)

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_url ON pages(url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_status ON pages(status_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_hash ON pages(content_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON crawl_queue(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_url)")

    def start_crawl(self) -> int:
        """Start a new crawl session. Returns crawl_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO crawl_info (domain, started_at, status)
                VALUES (?, ?, 'running')
            """, (self.domain, datetime.now().isoformat()))
            return cursor.lastrowid

    def complete_crawl(self, crawl_id: int):
        """Mark crawl as completed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Count only actual pages (200 OK), not redirects or errors
            cursor.execute("SELECT COUNT(*) FROM pages WHERE status_code = 200")
            pages_crawled = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM pages WHERE status_code >= 400 OR error_message IS NOT NULL")
            pages_with_errors = cursor.fetchone()[0]

            cursor.execute("""
                UPDATE crawl_info
                SET completed_at = ?, pages_crawled = ?, pages_with_errors = ?, status = 'completed'
                WHERE id = ?
            """, (datetime.now().isoformat(), pages_crawled, pages_with_errors, crawl_id))

    def add_to_queue(self, url: str, source_url: Optional[str] = None, depth: int = 0):
        """Add URL to crawl queue."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO crawl_queue (url, source_url, depth, added_at, status)
                    VALUES (?, ?, ?, ?, 'pending')
                """, (url, source_url, depth, datetime.now().isoformat()))
            except sqlite3.IntegrityError:
                pass  # URL already in queue

    def get_pending_urls(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get pending URLs from queue."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT url, source_url, depth FROM crawl_queue
                WHERE status = 'pending'
                ORDER BY depth ASC, id ASC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def mark_url_crawled(self, url: str):
        """Mark URL as crawled in queue."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE crawl_queue SET status = 'crawled' WHERE url = ?
            """, (url,))

    def mark_url_failed(self, url: str):
        """Mark URL as failed in queue."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE crawl_queue SET status = 'failed' WHERE url = ?
            """, (url,))

    def save_page(self, page: PageData):
        """Save or update page data."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            data = asdict(page)

            # Check if page exists
            cursor.execute("SELECT id FROM pages WHERE url = ?", (page.url,))
            existing = cursor.fetchone()

            if existing:
                # Update existing
                set_clause = ", ".join(f"{k} = ?" for k in data.keys() if k != 'url')
                values = [v for k, v in data.items() if k != 'url']
                values.append(page.url)
                cursor.execute(f"UPDATE pages SET {set_clause} WHERE url = ?", values)
            else:
                # Insert new
                columns = ", ".join(data.keys())
                placeholders = ", ".join("?" * len(data))
                cursor.execute(f"INSERT INTO pages ({columns}) VALUES ({placeholders})", list(data.values()))

    def get_page(self, url: str) -> Optional[PageData]:
        """Get page data by URL."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pages WHERE url = ?", (url,))
            row = cursor.fetchone()
            if row:
                # Filter out 'id' column which is not in PageData
                row_dict = {k: v for k, v in dict(row).items() if k != 'id'}
                return PageData(**row_dict)
            return None

    def get_all_pages(self) -> Iterator[PageData]:
        """Iterate over all pages."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pages")
            for row in cursor.fetchall():
                row_dict = {k: v for k, v in dict(row).items() if k != 'id'}
                yield PageData(**row_dict)

    def get_pages_by_status(self, status_code: int) -> List[PageData]:
        """Get all pages with specific status code."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pages WHERE status_code = ?", (status_code,))
            return [PageData(**{k: v for k, v in dict(row).items() if k != 'id'}) for row in cursor.fetchall()]

    def get_pages_count(self) -> int:
        """Get total number of crawled pages."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM pages")
            return cursor.fetchone()[0]

    def get_queue_count(self) -> Dict[str, int]:
        """Get queue statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, COUNT(*) as count FROM crawl_queue GROUP BY status
            """)
            return {row['status']: row['count'] for row in cursor.fetchall()}

    def save_link(self, source_url: str, target_url: str, anchor_text: str = None,
                  is_internal: bool = True, link_type: str = None, nofollow: bool = False):
        """Save a link relationship."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO links
                    (source_url, target_url, anchor_text, is_internal, link_type, nofollow)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (source_url, target_url, anchor_text, int(is_internal), link_type, int(nofollow)))
            except sqlite3.IntegrityError:
                pass

    def get_internal_links_to(self, url: str) -> List[Dict[str, Any]]:
        """Get all internal links pointing to a URL."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT source_url, anchor_text FROM links
                WHERE target_url = ? AND is_internal = 1
            """, (url,))
            return [dict(row) for row in cursor.fetchall()]

    def get_internal_links_from(self, url: str) -> List[Dict[str, Any]]:
        """Get all internal links from a URL."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT target_url, anchor_text FROM links
                WHERE source_url = ? AND is_internal = 1
            """, (url,))
            return [dict(row) for row in cursor.fetchall()]

    def save_sitemap_urls(self, urls: List[Dict[str, Any]]):
        """Save sitemap URLs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for url_data in urls:
                cursor.execute("""
                    INSERT OR REPLACE INTO sitemap_urls (url, lastmod, changefreq, priority)
                    VALUES (?, ?, ?, ?)
                """, (
                    url_data.get('url'),
                    url_data.get('lastmod'),
                    url_data.get('changefreq'),
                    url_data.get('priority')
                ))

    def get_sitemap_urls(self) -> List[Dict[str, Any]]:
        """Get all sitemap URLs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sitemap_urls")
            return [dict(row) for row in cursor.fetchall()]

    def save_robots_txt(self, content: str):
        """Save robots.txt content."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO robots_txt (content, fetched_at) VALUES (?, ?)
            """, (content, datetime.now().isoformat()))

    def get_robots_txt(self) -> Optional[str]:
        """Get robots.txt content."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM robots_txt ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return row['content'] if row else None

    def is_url_crawled(self, url: str) -> bool:
        """Check if URL has been crawled."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM pages WHERE url = ?", (url,))
            return cursor.fetchone() is not None

    def get_duplicate_groups(self, similarity_threshold: float = 0.85) -> List[List[str]]:
        """Get groups of pages with similar content hashes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content_hash, GROUP_CONCAT(url) as urls
                FROM pages
                WHERE content_hash IS NOT NULL
                GROUP BY content_hash
                HAVING COUNT(*) > 1
            """)
            return [row['urls'].split(',') for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """Get crawl statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Total pages (only 200 OK - actual pages analyzed)
            cursor.execute("SELECT COUNT(*) FROM pages WHERE status_code = 200")
            stats['total_pages'] = cursor.fetchone()[0]

            # Total URLs crawled (all status codes)
            cursor.execute("SELECT COUNT(*) FROM pages")
            stats['total_urls_crawled'] = cursor.fetchone()[0]

            # Redirect count (301, 302, 307, 308)
            cursor.execute("SELECT COUNT(*) FROM pages WHERE status_code IN (301, 302, 307, 308)")
            stats['total_redirects'] = cursor.fetchone()[0]

            # Error count (4xx, 5xx)
            cursor.execute("SELECT COUNT(*) FROM pages WHERE status_code >= 400")
            stats['total_errors'] = cursor.fetchone()[0]

            # Status code distribution
            cursor.execute("""
                SELECT status_code, COUNT(*) as count
                FROM pages GROUP BY status_code
            """)
            stats['status_codes'] = {row['status_code']: row['count'] for row in cursor.fetchall()}

            # Pages with issues
            cursor.execute("SELECT COUNT(*) FROM pages WHERE title IS NULL OR title = ''")
            stats['missing_title'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM pages WHERE meta_description IS NULL OR meta_description = ''")
            stats['missing_description'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM pages WHERE h1 IS NULL OR h1 = ''")
            stats['missing_h1'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM pages WHERE h1_count > 1")
            stats['multiple_h1'] = cursor.fetchone()[0]

            # Depth distribution
            cursor.execute("""
                SELECT depth, COUNT(*) as count
                FROM pages GROUP BY depth ORDER BY depth
            """)
            stats['depth_distribution'] = {row['depth']: row['count'] for row in cursor.fetchall()}

            return stats

    def clear_all(self):
        """Clear all data (for fresh crawl)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pages")
            cursor.execute("DELETE FROM crawl_queue")
            cursor.execute("DELETE FROM links")
            cursor.execute("DELETE FROM sitemap_urls")
            cursor.execute("DELETE FROM robots_txt")
            cursor.execute("DELETE FROM crawl_info")
