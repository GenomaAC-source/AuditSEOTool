"""Helper utilities for AuditSEO Tool."""

import re
from urllib.parse import urlparse, urlunparse
from typing import Optional, List, Dict, Any


def normalize_url(url: str, strict_trailing_slash: bool = False) -> str:
    """Normalize URL for consistent comparison.

    Args:
        url: URL to normalize
        strict_trailing_slash: If False (default), treat example.com/ and example.com as equivalent

    Returns:
        Normalized URL string
    """
    if not url:
        return ""

    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    parsed = urlparse(url)

    # Normalize components
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Normalize path - remove trailing slash for comparison
    # This makes example.com/ and example.com equivalent
    path = parsed.path
    if not strict_trailing_slash:
        # Remove trailing slash, treating "/" as empty path for homepage
        path = path.rstrip('/')
        if path == '':
            path = ''  # Homepage: both example.com and example.com/ become example.com
    else:
        # Keep trailing slash as-is except for non-root paths
        path = parsed.path.rstrip('/') if parsed.path != '/' else '/'

    # Remove default ports
    if ':80' in netloc and scheme == 'http':
        netloc = netloc.replace(':80', '')
    if ':443' in netloc and scheme == 'https':
        netloc = netloc.replace(':443', '')

    # Reconstruct URL without fragment
    return urlunparse((scheme, netloc, path, parsed.params, parsed.query, ''))


def extract_domain(url: str) -> str:
    """Extract domain from URL.

    Args:
        url: URL to extract domain from

    Returns:
        Domain string
    """
    parsed = urlparse(url)
    return parsed.netloc.lower()


def clean_text(text: str) -> str:
    """Clean and normalize text content.

    Args:
        text: Text to clean

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

    return text.strip()


def count_words(text: str) -> int:
    """Count words in text.

    Args:
        text: Text to count words in

    Returns:
        Word count
    """
    if not text:
        return 0
    return len(text.split())


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text or ""

    return text[:max_length - len(suffix)] + suffix


def is_valid_url(url: str) -> bool:
    """Check if URL is valid.

    Args:
        url: URL to validate

    Returns:
        True if valid
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def get_url_depth(url: str) -> int:
    """Get depth of URL based on path segments.

    Args:
        url: URL to analyze

    Returns:
        Depth (number of path segments)
    """
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    if not path:
        return 0
    return len(path.split('/'))


def extract_url_parts(url: str) -> Dict[str, Any]:
    """Extract all parts of a URL.

    Args:
        url: URL to parse

    Returns:
        Dictionary with URL parts
    """
    parsed = urlparse(url)
    return {
        'scheme': parsed.scheme,
        'domain': parsed.netloc,
        'path': parsed.path,
        'query': parsed.query,
        'fragment': parsed.fragment,
        'depth': get_url_depth(url)
    }


def has_trailing_slash(url: str) -> bool:
    """Check if URL has trailing slash.

    Args:
        url: URL to check

    Returns:
        True if has trailing slash
    """
    parsed = urlparse(url)
    return parsed.path.endswith('/') and parsed.path != '/'


def has_url_parameters(url: str) -> bool:
    """Check if URL has query parameters.

    Args:
        url: URL to check

    Returns:
        True if has parameters
    """
    parsed = urlparse(url)
    return bool(parsed.query)


def is_https(url: str) -> bool:
    """Check if URL uses HTTPS.

    Args:
        url: URL to check

    Returns:
        True if HTTPS
    """
    parsed = urlparse(url)
    return parsed.scheme.lower() == 'https'


def has_www(url: str) -> bool:
    """Check if URL has www prefix.

    Args:
        url: URL to check

    Returns:
        True if has www
    """
    parsed = urlparse(url)
    return parsed.netloc.lower().startswith('www.')


def url_uses_underscore(url: str) -> bool:
    """Check if URL path uses underscores.

    Args:
        url: URL to check

    Returns:
        True if uses underscores
    """
    parsed = urlparse(url)
    return '_' in parsed.path


def url_has_uppercase(url: str) -> bool:
    """Check if URL path has uppercase characters.

    Args:
        url: URL to check

    Returns:
        True if has uppercase
    """
    parsed = urlparse(url)
    return parsed.path != parsed.path.lower()


def url_has_double_slash(url: str) -> bool:
    """Check if URL has double slashes in path.

    Args:
        url: URL to check

    Returns:
        True if has double slashes
    """
    parsed = urlparse(url)
    return '//' in parsed.path


def format_number(n: int) -> str:
    """Format number with thousand separators.

    Args:
        n: Number to format

    Returns:
        Formatted string
    """
    return f"{n:,}".replace(',', '.')


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format value as percentage.

    Args:
        value: Value between 0 and 1
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{decimals}f}%"


def format_bytes(size: int) -> str:
    """Format bytes to human readable string.

    Args:
        size: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_milliseconds(ms: int) -> str:
    """Format milliseconds to human readable string.

    Args:
        ms: Time in milliseconds

    Returns:
        Formatted string (e.g., "1.5s")
    """
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms/1000:.2f}s"


def get_status_category(status_code: int) -> str:
    """Get category for HTTP status code.

    Args:
        status_code: HTTP status code

    Returns:
        Category string
    """
    if status_code == 0:
        return "error"
    elif 200 <= status_code < 300:
        return "success"
    elif 300 <= status_code < 400:
        return "redirect"
    elif 400 <= status_code < 500:
        return "client_error"
    elif 500 <= status_code < 600:
        return "server_error"
    else:
        return "unknown"


def validate_hreflang_code(code: str) -> bool:
    """Validate hreflang language/region code.

    Args:
        code: hreflang code to validate

    Returns:
        True if valid
    """
    if code == 'x-default':
        return True

    # Pattern: language or language-region
    pattern = r'^[a-z]{2}(-[A-Z]{2})?$'
    return bool(re.match(pattern, code, re.IGNORECASE))


def is_title_all_caps(title: str) -> bool:
    """Check if title is in all caps.

    Args:
        title: Title to check

    Returns:
        True if all caps
    """
    if not title:
        return False
    # Check if alphabetic characters are all uppercase
    alpha_chars = [c for c in title if c.isalpha()]
    if not alpha_chars:
        return False
    return all(c.isupper() for c in alpha_chars)


def estimate_title_pixel_width(title: str) -> int:
    """Estimate pixel width of title in search results.

    This is a rough estimation based on average character widths.

    Args:
        title: Title text

    Returns:
        Estimated pixel width
    """
    if not title:
        return 0

    # Average character widths (rough estimates)
    wide_chars = set('mwMW')
    narrow_chars = set('ijlIJ1!|.,;:\'"`')

    width = 0
    for char in title:
        if char in wide_chars:
            width += 12
        elif char in narrow_chars:
            width += 4
        elif char.isupper():
            width += 9
        else:
            width += 7

    return width


def estimate_description_pixel_width(description: str) -> int:
    """Estimate pixel width of meta description in search results.

    Args:
        description: Description text

    Returns:
        Estimated pixel width
    """
    # Similar logic to title but with smaller font
    if not description:
        return 0

    wide_chars = set('mwMW')
    narrow_chars = set('ijlIJ1!|.,;:\'"`')

    width = 0
    for char in description:
        if char in wide_chars:
            width += 10
        elif char in narrow_chars:
            width += 3
        elif char.isupper():
            width += 7
        else:
            width += 6

    return width
