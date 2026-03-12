"""Content analyzer for titles, descriptions, headings, images, and text."""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from ..database import CrawlDatabase, PageData
from ..utils.helpers import (
    is_title_all_caps, estimate_title_pixel_width,
    estimate_description_pixel_width, truncate_text
)


@dataclass
class TitleIssue:
    """Issue found with page title."""
    url: str
    title: Optional[str]
    issue_type: str
    description: str
    severity: str


@dataclass
class DescriptionIssue:
    """Issue found with meta description."""
    url: str
    description: Optional[str]
    issue_type: str
    detail: str
    severity: str


@dataclass
class HeadingIssue:
    """Issue found with headings."""
    url: str
    issue_type: str
    description: str
    headings: List[str] = field(default_factory=list)


@dataclass
class ImageIssue:
    """Issue found with images."""
    url: str
    image_src: str
    issue_type: str
    description: str


@dataclass
class ContentReport:
    """Complete content analysis report."""
    # Title analysis
    total_pages_analyzed: int = 0
    pages_with_title: int = 0
    pages_without_title: List[str] = field(default_factory=list)
    title_issues: List[TitleIssue] = field(default_factory=list)
    duplicate_titles: Dict[str, List[str]] = field(default_factory=dict)  # title -> [urls]
    title_length_distribution: Dict[str, int] = field(default_factory=dict)  # 'short', 'optimal', 'long'

    # Meta description analysis
    pages_with_description: int = 0
    pages_without_description: List[str] = field(default_factory=list)
    description_issues: List[DescriptionIssue] = field(default_factory=list)
    duplicate_descriptions: Dict[str, List[str]] = field(default_factory=dict)

    # Meta keywords
    pages_with_keywords: int = 0

    # Heading analysis
    pages_without_h1: List[str] = field(default_factory=list)
    pages_multiple_h1: List[Tuple[str, int]] = field(default_factory=list)  # (url, count)
    duplicate_h1: Dict[str, List[str]] = field(default_factory=dict)
    heading_issues: List[HeadingIssue] = field(default_factory=list)

    # Content analysis
    thin_content_pages: List[Tuple[str, int]] = field(default_factory=list)  # (url, word_count)
    word_count_distribution: Dict[str, int] = field(default_factory=dict)

    # Image analysis
    total_images: int = 0
    images_without_alt: int = 0
    images_empty_alt: int = 0
    images_generic_alt: int = 0
    image_issues: List[ImageIssue] = field(default_factory=list)


class ContentAnalyzer:
    """Analyzer for page content: titles, descriptions, headings, images."""

    # Thresholds
    TITLE_MIN_LENGTH = 30
    TITLE_MAX_LENGTH = 60
    TITLE_MAX_PIXEL_WIDTH = 600

    DESCRIPTION_MIN_LENGTH = 70
    DESCRIPTION_MAX_LENGTH = 160
    DESCRIPTION_MAX_PIXEL_WIDTH = 920

    THIN_CONTENT_THRESHOLD = 300  # words

    GENERIC_ALT_PATTERNS = [
        r'^image\d*$',
        r'^img\d*$',
        r'^foto\d*$',
        r'^immagine\d*$',
        r'^picture\d*$',
        r'^photo\d*$',
        r'^banner$',
        r'^logo$',
        r'^icon$',
        r'^\d+$',
        r'^dsc\d+$',
        r'^img_\d+$',
        r'^image_\d+$',
    ]

    def __init__(self, db: CrawlDatabase):
        """Initialize analyzer.

        Args:
            db: Database with crawl data
        """
        self.db = db
        self.report = ContentReport()

    def analyze(self) -> ContentReport:
        """Run complete content analysis.

        Returns:
            ContentReport with all findings
        """
        self._analyze_titles()
        self._analyze_descriptions()
        self._analyze_headings()
        self._analyze_content()
        self._analyze_images()

        return self.report

    def _analyze_titles(self):
        """Analyze page titles."""
        title_to_urls = defaultdict(list)
        length_counts = {'short': 0, 'optimal': 0, 'long': 0}

        for page in self.db.get_all_pages():
            if page.status_code != 200:
                continue

            self.report.total_pages_analyzed += 1

            if not page.title:
                self.report.pages_without_title.append(page.url)
                self.report.title_issues.append(TitleIssue(
                    url=page.url,
                    title=None,
                    issue_type='missing',
                    description='Title mancante',
                    severity='high'
                ))
                continue

            self.report.pages_with_title += 1
            title = page.title.strip()
            title_to_urls[title].append(page.url)

            # Check length
            title_len = len(title)
            if title_len < self.TITLE_MIN_LENGTH:
                length_counts['short'] += 1
                self.report.title_issues.append(TitleIssue(
                    url=page.url,
                    title=title,
                    issue_type='too_short',
                    description=f'Title troppo corto ({title_len} caratteri, min {self.TITLE_MIN_LENGTH})',
                    severity='medium'
                ))
            elif title_len > self.TITLE_MAX_LENGTH:
                length_counts['long'] += 1
                self.report.title_issues.append(TitleIssue(
                    url=page.url,
                    title=title,
                    issue_type='too_long',
                    description=f'Title troppo lungo ({title_len} caratteri, max {self.TITLE_MAX_LENGTH})',
                    severity='medium'
                ))
            else:
                length_counts['optimal'] += 1

            # Check pixel width
            pixel_width = estimate_title_pixel_width(title)
            if pixel_width > self.TITLE_MAX_PIXEL_WIDTH:
                self.report.title_issues.append(TitleIssue(
                    url=page.url,
                    title=title,
                    issue_type='pixel_overflow',
                    description=f'Title potrebbe essere troncato in SERP (~{pixel_width}px)',
                    severity='low'
                ))

            # Check all caps
            if is_title_all_caps(title):
                self.report.title_issues.append(TitleIssue(
                    url=page.url,
                    title=title,
                    issue_type='all_caps',
                    description='Title in maiuscolo',
                    severity='low'
                ))

            # Check generic titles
            generic_patterns = ['home', 'pagina', 'untitled', 'documento', 'page']
            if title.lower().strip() in generic_patterns:
                self.report.title_issues.append(TitleIssue(
                    url=page.url,
                    title=title,
                    issue_type='generic',
                    description='Title generico e poco descrittivo',
                    severity='high'
                ))

        # Find duplicates
        for title, urls in title_to_urls.items():
            if len(urls) > 1:
                self.report.duplicate_titles[title] = urls

        self.report.title_length_distribution = length_counts

    def _analyze_descriptions(self):
        """Analyze meta descriptions."""
        desc_to_urls = defaultdict(list)

        for page in self.db.get_all_pages():
            if page.status_code != 200:
                continue

            if not page.meta_description:
                self.report.pages_without_description.append(page.url)
                self.report.description_issues.append(DescriptionIssue(
                    url=page.url,
                    description=None,
                    issue_type='missing',
                    detail='Meta description mancante',
                    severity='medium'
                ))
                continue

            self.report.pages_with_description += 1
            desc = page.meta_description.strip()
            desc_to_urls[desc].append(page.url)

            # Check length
            desc_len = len(desc)
            if desc_len < self.DESCRIPTION_MIN_LENGTH:
                self.report.description_issues.append(DescriptionIssue(
                    url=page.url,
                    description=desc,
                    issue_type='too_short',
                    detail=f'Description troppo corta ({desc_len} caratteri)',
                    severity='low'
                ))
            elif desc_len > self.DESCRIPTION_MAX_LENGTH:
                self.report.description_issues.append(DescriptionIssue(
                    url=page.url,
                    description=desc,
                    issue_type='too_long',
                    detail=f'Description troppo lunga ({desc_len} caratteri)',
                    severity='low'
                ))

            # Check for call to action
            cta_patterns = ['scopri', 'acquista', 'leggi', 'visita', 'contatta',
                           'prenota', 'richiedi', 'trova', 'esplora', 'vedi']
            has_cta = any(cta in desc.lower() for cta in cta_patterns)
            if not has_cta:
                self.report.description_issues.append(DescriptionIssue(
                    url=page.url,
                    description=desc,
                    issue_type='no_cta',
                    detail='Description senza call to action',
                    severity='low'
                ))

            # Track keywords
            if page.meta_keywords:
                self.report.pages_with_keywords += 1

        # Find duplicates
        for desc, urls in desc_to_urls.items():
            if len(urls) > 1:
                self.report.duplicate_descriptions[truncate_text(desc, 50)] = urls

    def _analyze_headings(self):
        """Analyze heading structure."""
        h1_to_urls = defaultdict(list)

        for page in self.db.get_all_pages():
            if page.status_code != 200:
                continue

            # Check H1
            if not page.h1:
                self.report.pages_without_h1.append(page.url)
                self.report.heading_issues.append(HeadingIssue(
                    url=page.url,
                    issue_type='missing_h1',
                    description='H1 mancante'
                ))
            else:
                h1_to_urls[page.h1].append(page.url)

            # Check multiple H1
            if page.h1_count > 1:
                self.report.pages_multiple_h1.append((page.url, page.h1_count))
                self.report.heading_issues.append(HeadingIssue(
                    url=page.url,
                    issue_type='multiple_h1',
                    description=f'{page.h1_count} tag H1 nella pagina'
                ))

            # Check heading hierarchy
            if page.headings_json:
                try:
                    headings = json.loads(page.headings_json)
                    self._check_heading_hierarchy(page.url, headings)
                except json.JSONDecodeError:
                    pass

        # Find duplicate H1
        for h1, urls in h1_to_urls.items():
            if len(urls) > 1:
                self.report.duplicate_h1[h1] = urls

    def _check_heading_hierarchy(self, url: str, headings: Dict[str, List[str]]):
        """Check if heading hierarchy is correct."""
        # Check for skipped levels
        has_h1 = bool(headings.get('h1'))
        has_h2 = bool(headings.get('h2'))
        has_h3 = bool(headings.get('h3'))
        has_h4 = bool(headings.get('h4'))

        if has_h3 and not has_h2:
            self.report.heading_issues.append(HeadingIssue(
                url=url,
                issue_type='hierarchy_skip',
                description='H3 presente senza H2 (gerarchia saltata)',
                headings=headings.get('h3', [])[:3]
            ))

        if has_h4 and not has_h3:
            self.report.heading_issues.append(HeadingIssue(
                url=url,
                issue_type='hierarchy_skip',
                description='H4 presente senza H3 (gerarchia saltata)',
                headings=headings.get('h4', [])[:3]
            ))

        # Check for empty headings
        for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for heading in headings.get(level, []):
                if not heading or not heading.strip():
                    self.report.heading_issues.append(HeadingIssue(
                        url=url,
                        issue_type='empty_heading',
                        description=f'Tag {level.upper()} vuoto'
                    ))

    def _analyze_content(self):
        """Analyze text content."""
        word_counts = {'very_thin': 0, 'thin': 0, 'adequate': 0, 'rich': 0}

        for page in self.db.get_all_pages():
            if page.status_code != 200:
                continue

            word_count = page.word_count or 0

            if word_count < 100:
                word_counts['very_thin'] += 1
                self.report.thin_content_pages.append((page.url, word_count))
            elif word_count < self.THIN_CONTENT_THRESHOLD:
                word_counts['thin'] += 1
                self.report.thin_content_pages.append((page.url, word_count))
            elif word_count < 1000:
                word_counts['adequate'] += 1
            else:
                word_counts['rich'] += 1

        self.report.word_count_distribution = word_counts

    def _analyze_images(self):
        """Analyze images and alt text."""
        for page in self.db.get_all_pages():
            if page.status_code != 200 or not page.images_json:
                continue

            try:
                images = json.loads(page.images_json)

                for img in images:
                    self.report.total_images += 1
                    src = img.get('src', '')
                    alt = img.get('alt', '')

                    if alt is None:
                        self.report.images_without_alt += 1
                        self.report.image_issues.append(ImageIssue(
                            url=page.url,
                            image_src=src,
                            issue_type='missing_alt',
                            description='Attributo alt mancante'
                        ))
                    elif alt == '':
                        self.report.images_empty_alt += 1
                        self.report.image_issues.append(ImageIssue(
                            url=page.url,
                            image_src=src,
                            issue_type='empty_alt',
                            description='Attributo alt vuoto'
                        ))
                    else:
                        # Check for generic alt
                        alt_lower = alt.lower().strip()
                        is_generic = any(
                            re.match(pattern, alt_lower, re.IGNORECASE)
                            for pattern in self.GENERIC_ALT_PATTERNS
                        )
                        if is_generic:
                            self.report.images_generic_alt += 1
                            self.report.image_issues.append(ImageIssue(
                                url=page.url,
                                image_src=src,
                                issue_type='generic_alt',
                                description=f'Alt generico: "{alt}"'
                            ))

                        # Check alt too long
                        if len(alt) > 125:
                            self.report.image_issues.append(ImageIssue(
                                url=page.url,
                                image_src=src,
                                issue_type='alt_too_long',
                                description=f'Alt troppo lungo ({len(alt)} caratteri)'
                            ))

            except json.JSONDecodeError:
                pass

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of content analysis.

        Returns:
            Dictionary with summary data including example lists for AI analysis
        """
        # Get sample of title issues for AI
        long_titles = [
            {'url': issue.url, 'title': issue.title, 'length': len(issue.title) if issue.title else 0}
            for issue in self.report.title_issues
            if issue.issue_type == 'too_long'
        ][:10]

        short_titles = [
            {'url': issue.url, 'title': issue.title, 'length': len(issue.title) if issue.title else 0}
            for issue in self.report.title_issues
            if issue.issue_type == 'too_short'
        ][:10]

        # Get sample of images without alt
        images_without_alt_list = [
            {'page': issue.url, 'src': issue.image_src}
            for issue in self.report.image_issues
            if issue.issue_type == 'missing_alt'
        ][:15]

        return {
            'total_pages': self.report.total_pages_analyzed,
            'titles': {
                'with_title': self.report.pages_with_title,
                'without_title': len(self.report.pages_without_title),
                'without_title_list': self.report.pages_without_title[:15],
                'duplicates': len(self.report.duplicate_titles),
                'duplicate_titles': {k: v[:5] for k, v in list(self.report.duplicate_titles.items())[:5]},
                'length_distribution': self.report.title_length_distribution,
                'long_titles_list': long_titles,
                'short_titles_list': short_titles
            },
            'descriptions': {
                'with_description': self.report.pages_with_description,
                'without_description': len(self.report.pages_without_description),
                'without_description_list': self.report.pages_without_description[:15],
                'duplicates': len(self.report.duplicate_descriptions),
                'duplicate_descriptions': {k[:60]: v[:5] for k, v in list(self.report.duplicate_descriptions.items())[:5]}
            },
            'headings': {
                'without_h1': len(self.report.pages_without_h1),
                'without_h1_list': self.report.pages_without_h1[:15],
                'multiple_h1': len(self.report.pages_multiple_h1),
                'multiple_h1_list': self.report.pages_multiple_h1[:10],
                'duplicate_h1': len(self.report.duplicate_h1),
                'duplicate_h1_dict': {k: v[:5] for k, v in list(self.report.duplicate_h1.items())[:5]}
            },
            'content': {
                'thin_pages': len(self.report.thin_content_pages),
                'thin_pages_list': self.report.thin_content_pages[:10],
                'word_count_distribution': self.report.word_count_distribution
            },
            'images': {
                'total': self.report.total_images,
                'without_alt': self.report.images_without_alt,
                'without_alt_list': images_without_alt_list,
                'empty_alt': self.report.images_empty_alt,
                'generic_alt': self.report.images_generic_alt
            }
        }
