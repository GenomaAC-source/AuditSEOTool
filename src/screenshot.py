"""Screenshot capture using Playwright."""

import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


@dataclass
class ScreenshotConfig:
    """Configuration for screenshot capture."""
    width: int = 1920
    height: int = 1080
    mobile_width: int = 375
    mobile_height: int = 812
    full_page: bool = False
    quality: int = 80  # For JPEG
    timeout_ms: int = 30000


class ScreenshotCapture:
    """Capture screenshots of web pages using Playwright."""

    def __init__(
        self,
        output_dir: Path,
        config: ScreenshotConfig = None
    ):
        """Initialize screenshot capture.

        Args:
            output_dir: Directory to save screenshots
            config: Screenshot configuration
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright is not installed. "
                "Install it with: pip install playwright && playwright install"
            )

        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or ScreenshotConfig()
        self.browser: Optional[Browser] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        await self.playwright.stop()

    async def capture_page(
        self,
        url: str,
        filename: str,
        mobile: bool = False,
        full_page: bool = None,
        selector: str = None
    ) -> Optional[Path]:
        """Capture screenshot of a page.

        Args:
            url: URL to capture
            filename: Output filename (without extension)
            mobile: Capture mobile viewport
            full_page: Capture full page (overrides config)
            selector: Capture specific element

        Returns:
            Path to saved screenshot or None on error
        """
        if not self.browser:
            return None

        try:
            context = await self.browser.new_context(
                viewport={
                    'width': self.config.mobile_width if mobile else self.config.width,
                    'height': self.config.mobile_height if mobile else self.config.height
                },
                device_scale_factor=2 if mobile else 1,
                is_mobile=mobile
            )

            page = await context.new_page()
            await page.goto(url, timeout=self.config.timeout_ms, wait_until='networkidle')

            output_path = self.output_dir / f"{filename}.png"

            if selector:
                element = await page.query_selector(selector)
                if element:
                    await element.screenshot(path=str(output_path))
                else:
                    return None
            else:
                await page.screenshot(
                    path=str(output_path),
                    full_page=full_page if full_page is not None else self.config.full_page
                )

            await context.close()
            return output_path

        except Exception as e:
            print(f"Error capturing {url}: {e}")
            return None

    async def capture_code_snippet(
        self,
        html_content: str,
        filename: str,
        highlight_pattern: str = None
    ) -> Optional[Path]:
        """Capture screenshot of HTML code with syntax highlighting.

        Args:
            html_content: HTML code to display
            filename: Output filename
            highlight_pattern: Pattern to highlight in code

        Returns:
            Path to saved screenshot or None on error
        """
        if not self.browser:
            return None

        # Create HTML page with code
        escaped_html = html_content.replace('<', '&lt;').replace('>', '&gt;')

        if highlight_pattern:
            escaped_html = escaped_html.replace(
                highlight_pattern,
                f'<mark style="background-color: yellow;">{highlight_pattern}</mark>'
            )

        page_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 14px;
                    background: #f5f5f5;
                    padding: 20px;
                    margin: 0;
                }}
                pre {{
                    background: #1e1e1e;
                    color: #d4d4d4;
                    padding: 20px;
                    border-radius: 8px;
                    overflow-x: auto;
                    line-height: 1.5;
                }}
                mark {{
                    background-color: #ffd700;
                    color: #1e1e1e;
                    padding: 2px 4px;
                    border-radius: 3px;
                }}
            </style>
        </head>
        <body>
            <pre><code>{escaped_html}</code></pre>
        </body>
        </html>
        """

        try:
            context = await self.browser.new_context(
                viewport={'width': 800, 'height': 600}
            )
            page = await context.new_page()
            await page.set_content(page_html)

            output_path = self.output_dir / f"{filename}.png"
            await page.screenshot(path=str(output_path), full_page=True)

            await context.close()
            return output_path

        except Exception as e:
            print(f"Error capturing code snippet: {e}")
            return None

    async def capture_multiple(
        self,
        urls: List[str],
        prefix: str = "page"
    ) -> Dict[str, Path]:
        """Capture screenshots of multiple URLs.

        Args:
            urls: List of URLs to capture
            prefix: Filename prefix

        Returns:
            Dictionary mapping URLs to screenshot paths
        """
        results = {}

        for i, url in enumerate(urls):
            filename = f"{prefix}_{i+1}"
            path = await self.capture_page(url, filename)
            if path:
                results[url] = path

        return results


async def capture_audit_screenshots(
    base_url: str,
    output_dir: Path,
    urls_to_capture: List[str] = None,
    include_mobile: bool = True
) -> Dict[str, Path]:
    """Capture screenshots for audit report.

    Args:
        base_url: Base URL of the site
        output_dir: Directory to save screenshots
        urls_to_capture: Specific URLs to capture (default: homepage only)
        include_mobile: Include mobile screenshots

    Returns:
        Dictionary of screenshot paths
    """
    if not PLAYWRIGHT_AVAILABLE:
        return {}

    results = {}

    async with ScreenshotCapture(output_dir) as capture:
        # Homepage desktop
        homepage_path = await capture.capture_page(base_url, "homepage_desktop")
        if homepage_path:
            results['homepage_desktop'] = homepage_path

        # Homepage mobile
        if include_mobile:
            mobile_path = await capture.capture_page(base_url, "homepage_mobile", mobile=True)
            if mobile_path:
                results['homepage_mobile'] = mobile_path

        # Additional URLs
        if urls_to_capture:
            for i, url in enumerate(urls_to_capture[:10]):  # Limit to 10
                path = await capture.capture_page(url, f"page_{i+1}")
                if path:
                    results[url] = path

    return results


def is_playwright_available() -> bool:
    """Check if Playwright is available."""
    return PLAYWRIGHT_AVAILABLE
