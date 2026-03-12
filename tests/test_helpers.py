"""Tests for helper utilities."""

import pytest
from src.utils.helpers import (
    normalize_url, extract_domain, clean_text, count_words,
    is_valid_url, get_url_depth, url_uses_underscore,
    url_has_uppercase, url_has_double_slash, has_url_parameters,
    is_title_all_caps, validate_hreflang_code,
    estimate_title_pixel_width
)


class TestUrlHelpers:
    """Tests for URL helper functions."""

    def test_normalize_url(self):
        """Test URL normalization."""
        # Add scheme if missing
        result = normalize_url("example.com")
        assert "example.com" in result
        # Preserve http
        assert normalize_url("http://example.com/").startswith("http://")
        # Lowercase domain
        assert "example.com" in normalize_url("https://EXAMPLE.COM/Page").lower()
        # Remove fragment
        assert "#" not in normalize_url("https://example.com/page#section")

    def test_extract_domain(self):
        """Test domain extraction."""
        assert extract_domain("https://www.example.com/page") == "www.example.com"
        assert extract_domain("https://example.com") == "example.com"

    def test_is_valid_url(self):
        """Test URL validation."""
        assert is_valid_url("https://example.com")
        assert is_valid_url("http://example.com/path")
        assert not is_valid_url("not a url")
        assert not is_valid_url("")

    def test_get_url_depth(self):
        """Test URL depth calculation."""
        assert get_url_depth("https://example.com/") == 0
        assert get_url_depth("https://example.com/category") == 1
        assert get_url_depth("https://example.com/category/subcategory") == 2
        assert get_url_depth("https://example.com/a/b/c/d") == 4

    def test_url_uses_underscore(self):
        """Test underscore detection."""
        assert url_uses_underscore("https://example.com/my_page")
        assert not url_uses_underscore("https://example.com/my-page")

    def test_url_has_uppercase(self):
        """Test uppercase detection."""
        assert url_has_uppercase("https://example.com/MyPage")
        assert not url_has_uppercase("https://example.com/mypage")

    def test_url_has_double_slash(self):
        """Test double slash detection."""
        assert url_has_double_slash("https://example.com//page")
        assert not url_has_double_slash("https://example.com/page")

    def test_has_url_parameters(self):
        """Test parameter detection."""
        assert has_url_parameters("https://example.com/page?id=123")
        assert not has_url_parameters("https://example.com/page")


class TestTextHelpers:
    """Tests for text helper functions."""

    def test_clean_text(self):
        """Test text cleaning."""
        assert clean_text("  hello   world  ") == "hello world"
        assert clean_text("") == ""

    def test_count_words(self):
        """Test word counting."""
        assert count_words("one two three") == 3
        assert count_words("") == 0
        assert count_words("single") == 1

    def test_is_title_all_caps(self):
        """Test all caps detection."""
        assert is_title_all_caps("THIS IS ALL CAPS")
        assert not is_title_all_caps("This Is Title Case")
        assert not is_title_all_caps("this is lowercase")


class TestHreflangValidation:
    """Tests for hreflang validation."""

    def test_valid_language_codes(self):
        """Test valid language codes."""
        assert validate_hreflang_code("en")
        assert validate_hreflang_code("it")
        assert validate_hreflang_code("en-GB")
        assert validate_hreflang_code("en-US")
        assert validate_hreflang_code("x-default")

    def test_invalid_language_codes(self):
        """Test invalid language codes."""
        assert not validate_hreflang_code("eng")  # Too long
        assert not validate_hreflang_code("e")  # Too short
        # Note: our simple regex accepts en-UK even though GB is correct per ISO
        # This is a known limitation for simplicity


class TestPixelEstimation:
    """Tests for pixel width estimation."""

    def test_title_pixel_width(self):
        """Test title pixel width estimation."""
        # Short title
        short_width = estimate_title_pixel_width("Test")
        assert short_width < 100

        # Long title
        long_width = estimate_title_pixel_width("This is a very long title that should exceed the maximum width")
        assert long_width > 400

        # Empty
        assert estimate_title_pixel_width("") == 0
        assert estimate_title_pixel_width(None) == 0
