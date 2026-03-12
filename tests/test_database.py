"""Tests for database module."""

import pytest
import tempfile
from pathlib import Path

from src.database import CrawlDatabase, PageData


@pytest.fixture
def temp_db():
    """Create temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = CrawlDatabase("test.example.com", Path(tmpdir))
        yield db


class TestCrawlDatabase:
    """Tests for CrawlDatabase."""

    def test_init(self, temp_db):
        """Test database initialization."""
        assert temp_db.domain == "test.example.com"
        assert temp_db.db_path.exists()

    def test_save_and_get_page(self, temp_db):
        """Test saving and retrieving page."""
        page = PageData(
            url="https://test.example.com/page1",
            status_code=200,
            title="Test Page",
            meta_description="Test description",
            h1="Test H1",
            h1_count=1
        )
        temp_db.save_page(page)

        retrieved = temp_db.get_page("https://test.example.com/page1")
        assert retrieved is not None
        assert retrieved.title == "Test Page"
        assert retrieved.status_code == 200

    def test_queue_operations(self, temp_db):
        """Test crawl queue operations."""
        temp_db.add_to_queue("https://test.example.com/page1", depth=0)
        temp_db.add_to_queue("https://test.example.com/page2", depth=1)

        pending = temp_db.get_pending_urls(limit=10)
        assert len(pending) == 2

        temp_db.mark_url_crawled("https://test.example.com/page1")
        pending = temp_db.get_pending_urls(limit=10)
        assert len(pending) == 1

    def test_link_tracking(self, temp_db):
        """Test link tracking."""
        temp_db.save_link(
            source_url="https://test.example.com/page1",
            target_url="https://test.example.com/page2",
            anchor_text="Link to page 2",
            is_internal=True
        )

        links = temp_db.get_internal_links_from("https://test.example.com/page1")
        assert len(links) == 1
        assert links[0]['target_url'] == "https://test.example.com/page2"

    def test_statistics(self, temp_db):
        """Test statistics gathering."""
        # Add some pages
        for i in range(5):
            page = PageData(
                url=f"https://test.example.com/page{i}",
                status_code=200,
                title=f"Page {i}" if i < 3 else None,
                h1=f"H1 {i}" if i < 4 else None,
                h1_count=1 if i < 4 else 0
            )
            temp_db.save_page(page)

        stats = temp_db.get_statistics()
        assert stats['total_pages'] == 5
        assert stats['missing_title'] == 2
        assert stats['missing_h1'] == 1

    def test_clear_all(self, temp_db):
        """Test clearing database."""
        temp_db.add_to_queue("https://test.example.com/page1")
        temp_db.save_page(PageData(url="https://test.example.com/page1", status_code=200))

        temp_db.clear_all()

        assert temp_db.get_pages_count() == 0
        assert len(temp_db.get_pending_urls()) == 0
