"""
AuditSEO Tool - Web Interface
Interfaccia Streamlit professionale per audit SEO
"""

import streamlit as st
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import json
import time
import pandas as pd

# Fix asyncio event loop for Streamlit
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import CrawlDatabase
from src.crawler import AsyncCrawler
from src.analyzers import (
    ArchitectureAnalyzer,
    ContentAnalyzer,
    TechnicalAnalyzer,
    DuplicateAnalyzer,
    StructuredDataAnalyzer,
    PageClassifier,
    StrategicLinkingAnalyzer,
)
from src.reporters import MarkdownReporter, DocxReporter
from src.screenshot import capture_audit_screenshots, is_playwright_available

# AI imports
try:
    from src.ai.config import AIConfig, ProviderType
    from src.ai.feedback.storage import FeedbackStorage, SectionFeedback
    from src.ai.validation import (
        validate_claude_key,
        validate_openai_key,
        validate_gemini_key,
        get_models_for_provider,
        CLAUDE_MODELS,
        OPENAI_MODELS,
        GEMINI_MODELS,
    )
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# Page config - minimal, professional
st.set_page_config(
    page_title="AuditSEO Tool",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - modern, clean design system
st.markdown("""
<style>
    /* ===== CSS VARIABLES ===== */
    :root {
        /* Primary colors */
        --primary: #0f172a;
        --primary-light: #1e293b;
        --accent: #3b82f6;
        --accent-hover: #2563eb;

        /* Backgrounds */
        --bg-main: #ffffff;
        --bg-secondary: #f8fafc;
        --bg-card: #ffffff;

        /* Borders */
        --border: #e2e8f0;
        --border-accent: #3b82f6;

        /* Status colors */
        --success: #10b981;
        --warning: #f59e0b;
        --error: #ef4444;

        /* Text colors */
        --text-primary: #0f172a;
        --text-secondary: #64748b;
        --text-muted: #94a3b8;

        /* Spacing */
        --space-xs: 0.25rem;
        --space-sm: 0.5rem;
        --space-md: 1rem;
        --space-lg: 1.5rem;
        --space-xl: 2rem;
        --space-2xl: 3rem;
    }

    /* ===== HIDE STREAMLIT BRANDING ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ===== TYPOGRAPHY ===== */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    .main .block-container {
        padding-top: var(--space-xl);
        padding-bottom: var(--space-xl);
        max-width: 1200px;
    }

    h1 {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.025em !important;
        margin-bottom: var(--space-sm) !important;
    }

    h2 {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        margin-top: var(--space-lg) !important;
        margin-bottom: var(--space-md) !important;
    }

    h3 {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
    }

    p, li, span {
        font-size: 0.95rem;
        line-height: 1.6;
        color: var(--text-primary);
    }

    /* ===== SIDEBAR STYLING ===== */
    [data-testid="stSidebar"] {
        background-color: var(--bg-secondary) !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding: var(--space-lg) !important;
    }

    /* Sidebar headers */
    [data-testid="stSidebar"] h1 {
        font-size: 1.5rem !important;
        margin-bottom: var(--space-xs) !important;
    }

    [data-testid="stSidebar"] h2 {
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        color: var(--text-muted) !important;
        font-weight: 500 !important;
        margin-top: var(--space-lg) !important;
        margin-bottom: var(--space-sm) !important;
        border-bottom: none !important;
    }

    /* Section labels */
    .section-label {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        font-weight: 500;
        margin-bottom: var(--space-xs);
    }

    /* ===== INPUT FIELDS ===== */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
        padding: 0.625rem 0.875rem !important;
        font-size: 0.95rem !important;
        background: white !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    }

    /* ===== BUTTONS ===== */
    /* Primary button (Avvia Audit) */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {
        background: var(--accent) !important;
        color: white !important;
        padding: 0.875rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        border-radius: 6px !important;
        border: none !important;
        transition: background 0.15s ease !important;
    }

    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="baseButton-primary"]:hover {
        background: var(--accent-hover) !important;
    }

    /* Secondary/outline buttons */
    .stButton > button:not([kind="primary"]):not([data-testid="baseButton-primary"]) {
        background: transparent !important;
        color: var(--text-primary) !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
    }

    .stButton > button:not([kind="primary"]):not([data-testid="baseButton-primary"]):hover {
        background: var(--bg-secondary) !important;
        border-color: #cbd5e1 !important;
    }

    /* Download buttons */
    .stDownloadButton > button {
        background: transparent !important;
        color: var(--text-primary) !important;
        padding: 0.625rem 1rem !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
    }

    .stDownloadButton > button:hover {
        background: var(--bg-secondary) !important;
        border-color: #cbd5e1 !important;
    }

    /* ===== METRIC CARDS ===== */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: var(--space-md) 1.25rem;
        margin-bottom: var(--space-sm);
    }

    .metric-card-error { border-left: 3px solid var(--error); }
    .metric-card-warning { border-left: 3px solid var(--warning); }
    .metric-card-success { border-left: 3px solid var(--success); }
    .metric-card-info { border-left: 3px solid var(--accent); }

    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--text-primary);
        line-height: 1;
    }

    .metric-label {
        font-size: 0.75rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: var(--space-xs);
    }

    /* ===== SEVERITY BADGES ===== */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.625rem;
        font-size: 0.7rem;
        font-weight: 600;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }

    .badge-critical {
        background: #fef2f2;
        color: #dc2626;
    }

    .badge-warning {
        background: #fffbeb;
        color: #d97706;
    }

    .badge-ok {
        background: #f0fdf4;
        color: #16a34a;
    }

    .badge-info {
        background: #eff6ff;
        color: #2563eb;
    }

    /* ===== EXPANDERS ===== */
    .streamlit-expanderHeader {
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        color: var(--text-primary) !important;
        background: transparent !important;
    }

    .streamlit-expanderHeader:hover {
        color: var(--accent) !important;
    }

    /* ===== STATUS INDICATORS ===== */
    .status-ok { color: var(--success); }
    .status-warning { color: var(--warning); }
    .status-error { color: var(--error); }

    /* ===== TABLES ===== */
    .dataframe {
        font-size: 0.9rem;
        border: 1px solid var(--border) !important;
    }

    /* ===== PROGRESS SECTION ===== */
    .progress-section {
        background: var(--bg-secondary);
        padding: var(--space-md);
        border-radius: 6px;
        margin: var(--space-md) 0;
    }

    /* ===== RESULTS HEADER ===== */
    .results-header {
        background: var(--bg-secondary);
        padding: var(--space-lg);
        border-radius: 8px;
        margin-bottom: var(--space-lg);
    }

    .results-header h2 {
        margin: 0 !important;
        font-size: 1.25rem !important;
    }

    .results-meta {
        color: var(--text-secondary);
        font-size: 0.875rem;
        margin-top: var(--space-xs);
    }

    /* ===== SECTION DIVIDERS ===== */
    hr {
        border: none;
        border-top: 1px solid var(--border);
        margin: var(--space-lg) 0;
    }

    /* ===== TABS STYLING ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 1px solid var(--border);
    }

    .stTabs [data-baseweb="tab"] {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-secondary);
        padding: var(--space-sm) var(--space-md);
        border-bottom: 2px solid transparent;
    }

    .stTabs [aria-selected="true"] {
        color: var(--accent) !important;
        border-bottom-color: var(--accent) !important;
        background: transparent !important;
    }

    /* ===== ALERTS/MESSAGES ===== */
    .stAlert {
        border-radius: 6px !important;
        border: none !important;
    }

    /* ===== CHECKBOX STYLING ===== */
    .stCheckbox {
        padding: var(--space-xs) 0;
    }
</style>
""", unsafe_allow_html=True)


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc or url


def get_site_name(url: str) -> str:
    """Get site name from URL."""
    domain = extract_domain(url)
    name = domain.replace('www.', '').split('.')[0]
    return name.title()


def _generate_narratives_for_display(narrative_gen, arch_data, content_data, tech_data, dup_data, struct_data, strategic_data=None, ai_config=None, ai_orchestrator=None):
    """Generate all narrative sections for display in UI.

    Uses AI if available, otherwise falls back to template.

    Returns dict with section_key -> {title, premise, situation, improvements, examples, source}
    """
    from src.reporters.narrative import NarrativeGenerator

    narratives = {}

    # Prepare linking data with strategic info
    linking_data = {**tech_data}
    if strategic_data:
        linking_data['strategic_linking'] = strategic_data

    # Map of section_key -> (title, generator_method, data)
    sections = [
        # Architettura
        ('alberatura', 'Alberatura', lambda: narrative_gen.generate_alberatura(arch_data), arch_data),
        ('canonical', 'Canonicalizzazione', lambda: narrative_gen.generate_canonical(arch_data, dup_data), {**arch_data, 'duplicates_data': dup_data}),
        ('hreflang', 'Hreflang', lambda: narrative_gen.generate_hreflang(arch_data), arch_data),
        ('url', 'Struttura URL', lambda: narrative_gen.generate_url(arch_data), arch_data),
        # Contenuti
        ('title', 'Meta Title', lambda: narrative_gen.generate_title(content_data), content_data),
        ('description', 'Meta Description', lambda: narrative_gen.generate_description(content_data), content_data),
        ('headings', 'Intestazioni (H1-H6)', lambda: narrative_gen.generate_headings(content_data), content_data),
        ('images', 'Immagini', lambda: narrative_gen.generate_images(content_data), content_data),
        ('linking', 'Linking Interno Strategico', lambda: narrative_gen.generate_linking(linking_data), linking_data),
        # Tecnico
        ('performance', 'Performance', lambda: narrative_gen.generate_performance(tech_data), tech_data),
        ('sitemap', 'Sitemap', lambda: narrative_gen.generate_sitemap(tech_data), tech_data),
        ('robots', 'Robots.txt', lambda: narrative_gen.generate_robots(tech_data), tech_data),
        ('https', 'HTTPS', lambda: narrative_gen.generate_https(tech_data), tech_data),
        ('errors', 'Errori 404 e Redirect', lambda: narrative_gen.generate_errors(tech_data), tech_data),
        ('structured_data', 'Dati Strutturati', lambda: narrative_gen.generate_structured_data(struct_data), struct_data),
    ]

    for section_key, title, template_gen_func, data in sections:
        source = 'template'
        try:
            # Try AI first if available
            if ai_orchestrator is not None:
                try:
                    result = ai_orchestrator.generate_section_safe(section_key, data)
                    if result.success and result.current_situation and result.source.value != 'template':
                        narratives[section_key] = {
                            'title': title,
                            'premise': narrative_gen.get_premise(section_key),
                            'situation': result.current_situation,
                            'improvements': result.improvements or "Non sono necessari miglioramenti significativi.",
                            'severity': 2,
                            'data': data,
                            'source': result.source.value,
                            'model': result.model,
                        }
                        continue  # Skip template generation
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"AI generation failed for {section_key}: {e}")

            # Fallback to template
            section = template_gen_func()
            narratives[section_key] = {
                'title': title,
                'premise': section.premise,
                'situation': section.current_situation,
                'improvements': section.improvements,
                'severity': getattr(section, 'severity', 2),
                'data': data,
                'source': 'template',
                'model': None,
            }
        except Exception as e:
            narratives[section_key] = {
                'title': title,
                'premise': narrative_gen.get_premise(section_key),
                'situation': f"Errore nella generazione: {str(e)}",
                'improvements': "Non disponibile",
                'severity': 2,
                'data': data,
                'source': 'error',
                'model': None,
            }

    return narratives


def get_ai_config_from_session() -> "AIConfig":
    """Build AIConfig from session state."""
    import logging
    logger = logging.getLogger(__name__)

    if not AI_AVAILABLE:
        logger.warning("[AI Config] AI modules not available")
        return None

    if not st.session_state.get('use_ai', False):
        logger.warning("[AI Config] use_ai is False")
        return None

    config = AIConfig()
    config.enabled = True

    # Get API keys from session
    claude_key = st.session_state.get('claude_api_key', '')
    openai_key = st.session_state.get('openai_api_key', '')
    gemini_key = st.session_state.get('gemini_api_key', '')

    # Debug logging
    logger.info(f"[AI Config] use_ai={st.session_state.get('use_ai')}")
    logger.info(f"[AI Config] claude_validated={st.session_state.get('claude_validated')}, key_present={bool(claude_key)}")
    logger.info(f"[AI Config] openai_validated={st.session_state.get('openai_validated')}, key_present={bool(openai_key)}")
    logger.info(f"[AI Config] gemini_validated={st.session_state.get('gemini_validated')}, key_present={bool(gemini_key)}")

    # Only use validated keys
    if claude_key and st.session_state.get('claude_validated', False):
        config.claude.api_key = claude_key
        config.claude.model = st.session_state.get('claude_model', CLAUDE_MODELS[0][0])
    if openai_key and st.session_state.get('openai_validated', False):
        config.openai.api_key = openai_key
        config.openai.model = st.session_state.get('openai_model', OPENAI_MODELS[0][0])
    if gemini_key and st.session_state.get('gemini_validated', False):
        config.gemini.api_key = gemini_key
        config.gemini.model = st.session_state.get('gemini_model', GEMINI_MODELS[0][0])

    # Check environment variables as fallback (assume valid)
    if not config.claude.api_key:
        env_key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY')
        if env_key:
            config.claude.api_key = env_key
    if not config.openai.api_key:
        env_key = os.getenv('OPENAI_API_KEY')
        if env_key:
            config.openai.api_key = env_key
    if not config.gemini.api_key:
        env_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        if env_key:
            config.gemini.api_key = env_key

    return config


def run_audit(url: str, max_pages: int, screenshots: bool, similarity: float,
              concurrency: int, delay: int, progress_callback=None, ai_config=None):
    """Run the audit and return results."""

    domain = extract_domain(url)
    site_name = get_site_name(url)

    # Setup paths
    data_dir = Path('data')
    domain_dir = data_dir / domain.replace('.', '_').replace(':', '_')
    screenshots_dir = domain_dir / 'screenshots'

    # Initialize database
    db = CrawlDatabase(domain, data_dir)

    results = {
        'domain': domain,
        'site_name': site_name,
        'stages': {},
        'reports': {},
        'summary': {}
    }

    # Stage 1: Crawl
    if progress_callback:
        progress_callback("Crawling del sito...", 0.1)

    crawler = AsyncCrawler(
        start_url=url,
        db=db,
        max_pages=max_pages if max_pages > 0 else None,
        concurrency=concurrency,
        delay_ms=delay
    )

    # Run crawl
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stats = loop.run_until_complete(crawler.crawl(resume=False))

    results['stages']['crawl'] = stats
    results['summary']['total_pages'] = stats.get('total_pages', 0)  # Only 200 OK
    results['summary']['total_urls_crawled'] = stats.get('total_urls_crawled', 0)  # All URLs
    results['summary']['total_redirects'] = stats.get('total_redirects', 0)  # 301, 302, etc.
    results['summary']['total_errors'] = stats.get('total_errors', 0)  # 4xx, 5xx

    if progress_callback:
        progress_callback(f"Crawlate {stats.get('total_urls_crawled', 0)} URL, {stats.get('total_pages', 0)} pagine analizzate", 0.3)

    # Collect pages list for display
    pages_list = []
    for page in db.get_all_pages():
        pages_list.append({
            'URL': page.url,
            'Status': page.status_code,
            'Title': (page.title[:60] + '...') if page.title and len(page.title) > 60 else (page.title or ''),
            'H1': (page.h1[:40] + '...') if page.h1 and len(page.h1) > 40 else (page.h1 or ''),
            'Depth': page.depth,
            'Words': page.word_count,
            'Load (ms)': page.load_time_ms or 0,
        })
    results['pages_list'] = pages_list

    # Stage 2: Analysis
    if progress_callback:
        progress_callback("Analisi architettura...", 0.4)

    arch_analyzer = ArchitectureAnalyzer(db)
    arch_report = arch_analyzer.analyze()
    arch_summary = arch_analyzer.get_summary()

    if progress_callback:
        progress_callback("Analisi contenuti...", 0.5)

    content_analyzer = ContentAnalyzer(db)
    content_report = content_analyzer.analyze()
    content_summary = content_analyzer.get_summary()

    if progress_callback:
        progress_callback("Analisi tecnica...", 0.6)

    tech_analyzer = TechnicalAnalyzer(db, url)
    tech_report = tech_analyzer.analyze()
    tech_summary = tech_analyzer.get_summary()

    if progress_callback:
        progress_callback("Analisi duplicati...", 0.7)

    dup_analyzer = DuplicateAnalyzer(db, similarity)
    dup_report = dup_analyzer.analyze()
    dup_summary = dup_analyzer.get_summary()

    if progress_callback:
        progress_callback("Analisi dati strutturati...", 0.75)

    struct_analyzer = StructuredDataAnalyzer(db)
    struct_report = struct_analyzer.analyze()
    struct_summary = struct_analyzer.get_summary()

    # Strategic Linking Analysis (with AI classification if available)
    if progress_callback:
        progress_callback("Analisi linking strategico...", 0.78)

    strategic_summary = {}
    try:
        # Classify pages using AI if available
        page_classifier = PageClassifier(db, ai_config)
        use_ai = ai_config is not None and ai_config.enabled
        classification_report = page_classifier.classify_all(use_ai=use_ai)

        # Analyze strategic linking
        strategic_analyzer = StrategicLinkingAnalyzer(db, classification_report)
        strategic_report = strategic_analyzer.analyze()
        strategic_summary = strategic_analyzer.get_summary()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Strategic linking analysis failed: {e}")
        strategic_summary = {'error': str(e)}

    results['stages']['analysis'] = {
        'architecture': arch_summary,
        'content': content_summary,
        'technical': tech_summary,
        'duplicates': dup_summary,
        'structured_data': struct_summary,
        'strategic_linking': strategic_summary
    }

    # Stage 3: Screenshots (optional)
    screenshot_paths = {}
    if screenshots and is_playwright_available():
        if progress_callback:
            progress_callback("Cattura screenshot...", 0.8)
        try:
            screenshot_paths = loop.run_until_complete(
                capture_audit_screenshots(url, screenshots_dir, include_mobile=True)
            )
        except Exception as e:
            results['stages']['screenshots_error'] = str(e)

    # Stage 4: Reports
    if progress_callback:
        progress_callback("Generazione report...", 0.9)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"audit_{domain.replace('.', '_')}_{timestamp}"

    # Markdown
    md_reporter = MarkdownReporter(site_name, url, domain_dir)
    md_content = md_reporter.generate(
        arch_summary, content_summary, tech_summary,
        dup_summary, struct_summary,
        screenshots_dir if screenshot_paths else None
    )
    md_path = md_reporter.save(md_content, f"{base_filename}.md")
    results['reports']['markdown'] = {
        'path': str(md_path),
        'content': md_content
    }

    # DOCX
    docx_reporter = DocxReporter(site_name, url, domain_dir, ai_config=ai_config)
    docx_reporter.generate(
        arch_summary, content_summary, tech_summary,
        dup_summary, struct_summary,
        screenshots_dir if screenshot_paths else None,
        strategic_linking_data=strategic_summary
    )
    docx_path = docx_reporter.save(f"Audit SEO - {site_name} - {timestamp}.docx")
    results['reports']['docx'] = {'path': str(docx_path)}

    # Store AI status for user notification
    results['ai_status'] = docx_reporter.get_ai_status()
    results['generation_results'] = docx_reporter.get_generation_results()

    # Get AI orchestrator for UI narrative generation
    ai_orchestrator = None
    if ai_config is not None:
        try:
            from src.ai.orchestrator import AIOrchestrator
            from src.ai.feedback.storage import FeedbackStorage
            feedback_storage = FeedbackStorage()
            ai_orchestrator = AIOrchestrator(
                config=ai_config,
                site_name=site_name,
                site_url=url,
                feedback_storage=feedback_storage
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to create AI orchestrator for UI: {e}")

    # Store generated narratives for display and feedback (now uses AI!)
    results['narratives'] = _generate_narratives_for_display(
        docx_reporter.narrative,
        arch_summary, content_summary, tech_summary,
        dup_summary, struct_summary,
        strategic_data=strategic_summary,
        ai_config=ai_config,
        ai_orchestrator=ai_orchestrator
    )

    # Store screenshot paths
    results['screenshots'] = screenshot_paths

    # JSON
    json_path = domain_dir / f"{base_filename}_data.json"
    json_data = {
        'url': url,
        'domain': domain,
        'crawled_at': timestamp,
        'architecture': arch_summary,
        'content': content_summary,
        'technical': tech_summary,
        'duplicates': dup_summary,
        'structured_data': struct_summary
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    results['reports']['json'] = {
        'path': str(json_path),
        'data': json_data
    }

    # Build summary
    results['summary'].update({
        'orphan_pages': arch_summary.get('orphan_pages_count', 0),
        'canonical_missing': arch_summary.get('canonical_issues', {}).get('missing', 0),
        'without_title': content_summary.get('titles', {}).get('without_title', 0),
        'without_h1': content_summary.get('headings', {}).get('without_h1', 0),
        'without_description': content_summary.get('descriptions', {}).get('without_description', 0),
        'duplicates': dup_summary.get('duplicates', {}).get('exact', 0),
        'errors_404': tech_summary.get('redirects', {}).get('internal_to_404', 0),
        'pages_with_schema': struct_summary.get('pages_with_schema', 0)
    })

    if progress_callback:
        progress_callback("Completato", 1.0)

    loop.close()
    return results


def render_feedback_widget(section_key: str, section_title: str, generated_text: str = ""):
    """Render feedback widget for a section."""
    if not AI_AVAILABLE or not st.session_state.get('use_ai', False):
        return

    st.markdown("---")
    st.markdown("**Feedback su questa sezione**")

    col1, col2 = st.columns([1, 3])

    with col1:
        rating = st.slider(
            "Valutazione",
            min_value=1,
            max_value=5,
            value=3,
            key=f"rating_{section_key}",
            help="1 = Scarso, 5 = Eccellente"
        )
        st.caption(f"{rating}/5")

    with col2:
        feedback_text = st.text_area(
            "Il tuo feedback",
            placeholder="Es: Troppo generico, aggiungi riferimenti specifici alle pagine...",
            key=f"feedback_{section_key}",
            height=80
        )

    if st.button("Salva feedback", key=f"save_fb_{section_key}"):
        if feedback_text.strip():
            try:
                storage = FeedbackStorage()
                feedback = SectionFeedback(
                    section_type=section_key,
                    generated_text=generated_text,
                    user_feedback=feedback_text,
                    rating=rating
                )
                storage.add_section_feedback(
                    audit_id=st.session_state.get('audit_id', 'unknown'),
                    site_url=st.session_state.results.get('domain', ''),
                    section_key=section_key,
                    feedback=feedback
                )
                st.success("Feedback salvato!")
            except Exception as e:
                st.error(f"Errore nel salvataggio: {e}")
        else:
            st.warning("Inserisci un commento prima di salvare")


def render_narrative_section(section_key: str, narrative: dict, raw_data: dict, examples_key: str = None):
    """Render a complete narrative section with text, examples, and feedback.

    Args:
        section_key: Unique key for this section
        narrative: Dict with title, premise, situation, improvements
        raw_data: Raw analysis data for showing examples
        examples_key: Key to extract example URLs/items from raw_data
    """
    # Section header with severity badge
    severity = narrative.get('severity', 2)
    if severity == 1:
        badge_class = "badge-critical"
        badge_text = "Critico"
    elif severity == 2:
        badge_class = "badge-warning"
        badge_text = "Attenzione"
    else:
        badge_class = "badge-ok"
        badge_text = "OK"

    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
        <span style="font-weight: 600;">{narrative.get('title', section_key.title())}</span>
        <span class="badge {badge_class}">{badge_text}</span>
    </div>
    """, unsafe_allow_html=True)

    # Tabs for different content (no emojis)
    tab1, tab2, tab3 = st.tabs(["Analisi", "Dati", "Feedback"])

    with tab1:
        # Premise (collapsible)
        with st.expander("Premessa tecnica", expanded=False):
            st.markdown(f"*{narrative.get('premise', '')}*")

        # Situation
        st.markdown("**Situazione attuale:**")
        st.markdown(narrative.get('situation', 'Non disponibile'))

        # Improvements
        st.markdown("**Come migliorare:**")
        st.markdown(narrative.get('improvements', 'Non disponibile'))

    with tab2:
        # Show raw data and examples
        st.markdown("**Dati rilevati:**")

        # Extract and display relevant examples based on section type
        _display_section_examples(section_key, raw_data)

    with tab3:
        # Full text for feedback reference
        full_text = f"{narrative.get('situation', '')}\n\n{narrative.get('improvements', '')}"
        render_feedback_widget(section_key, narrative.get('title', ''), full_text)


def _display_section_examples(section_key: str, data: dict):
    """Display examples and data specific to each section type."""

    if section_key == 'alberatura':
        depth_dist = data.get('depth_distribution', {})
        if depth_dist:
            st.markdown("**Distribuzione per profondità:**")
            for depth, count in sorted(depth_dist.items(), key=lambda x: int(x[0])):
                pct = "█" * min(int(count / 10), 20)
                st.text(f"Livello {depth}: {count} pagine {pct}")

        orphans = data.get('orphan_pages', [])
        if orphans and isinstance(orphans, list):
            st.markdown("**Esempi pagine orfane:**")
            for url in orphans[:5]:
                st.code(url, language=None)
        elif data.get('orphan_pages_count', 0) > 0:
            st.warning(f"{data.get('orphan_pages_count')} pagine orfane rilevate")

        deep_pages = data.get('deep_pages', [])
        if deep_pages and isinstance(deep_pages, list):
            st.markdown("**Esempi pagine troppo profonde (>3 click):**")
            for url in deep_pages[:5]:
                st.code(url, language=None)

    elif section_key == 'canonical':
        missing = data.get('canonical_issues', {}).get('missing_list', [])
        if missing:
            st.markdown("**Pagine senza canonical:**")
            for url in missing[:5]:
                st.code(url, language=None)

        mismatches = data.get('canonical_issues', {}).get('mismatches_list', [])
        if mismatches:
            st.markdown("**Canonical non corrispondenti:**")
            for item in mismatches[:3]:
                if isinstance(item, dict):
                    st.text(f"Pagina: {item.get('url', 'N/A')}")
                    st.text(f"Canonical: {item.get('canonical', 'N/A')}")
                    st.markdown("---")

    elif section_key == 'title':
        titles = data.get('titles', {})
        without = titles.get('without_title_list', [])
        if without:
            st.markdown("**Pagine senza title:**")
            for url in without[:5]:
                st.code(url, language=None)

        duplicates = titles.get('duplicate_titles', {})
        if duplicates:
            st.markdown("**Title duplicati:**")
            for title, urls in list(duplicates.items())[:3]:
                st.text(f"Title: \"{title[:60]}...\"" if len(title) > 60 else f"Title: \"{title}\"")
                st.text(f"Usato in {len(urls)} pagine")
                st.markdown("---")

    elif section_key == 'description':
        desc = data.get('descriptions', {})
        without = desc.get('without_description_list', [])
        if without:
            st.markdown("**Pagine senza description:**")
            for url in without[:5]:
                st.code(url, language=None)

    elif section_key == 'headings':
        headings = data.get('headings', {})
        without_h1 = headings.get('without_h1_list', [])
        if without_h1:
            st.markdown("**Pagine senza H1:**")
            for url in without_h1[:5]:
                st.code(url, language=None)

        multiple_h1 = headings.get('multiple_h1_list', [])
        if multiple_h1:
            st.markdown("**Pagine con H1 multipli:**")
            for url in multiple_h1[:5]:
                st.code(url, language=None)

    elif section_key == 'images':
        images = data.get('images', {})
        st.markdown(f"**Totale immagini:** {images.get('total', 0)}")
        st.markdown(f"**Senza alt:** {images.get('without_alt', 0)}")
        st.markdown(f"**Alt vuoto:** {images.get('empty_alt', 0)}")
        st.markdown(f"**Alt generico:** {images.get('generic_alt', 0)}")

        without_alt = images.get('without_alt_list', [])
        if without_alt:
            st.markdown("**Esempi immagini senza alt:**")
            for img in without_alt[:5]:
                if isinstance(img, dict):
                    st.code(f"Pagina: {img.get('page', 'N/A')}\nImmagine: {img.get('src', 'N/A')}", language=None)
                else:
                    st.code(str(img), language=None)

    elif section_key == 'linking':
        linking = data.get('internal_linking', {})
        orphans = linking.get('orphan_pages_list', [])
        if orphans:
            st.markdown("**Pagine orfane (no link in ingresso):**")
            for url in orphans[:5]:
                st.code(url, language=None)

    elif section_key == 'performance':
        perf = data.get('performance', {})
        avg_time = perf.get('avg_load_time_ms', 0)
        st.metric("Tempo medio caricamento", f"{avg_time/1000:.2f}s")

        slow_pages = perf.get('slow_pages_list', [])
        if slow_pages:
            st.markdown("**Pagine lente (>3s):**")
            for item in slow_pages[:5]:
                if isinstance(item, dict):
                    st.text(f"{item.get('url', 'N/A')}: {item.get('time_ms', 0)/1000:.2f}s")
                else:
                    st.code(str(item), language=None)

    elif section_key == 'structured_data':
        st.markdown(f"**Pagine con schema:** {data.get('pages_with_schema', 0)} / {data.get('total_pages', 0)}")

        types = data.get('schema_types', {})
        if types:
            st.markdown("**Tipi Schema.org rilevati:**")
            for schema_type, count in types.items():
                st.text(f"  • {schema_type}: {count} pagine")

        issues = data.get('issues', {})
        if issues.get('errors', 0) > 0:
            st.warning(f"{issues.get('errors')} errori di validazione rilevati")

    else:
        # Generic display for unknown sections
        st.json(data)


def display_metric(label: str, value, status: str = None):
    """Display a metric in clean style."""
    status_class = ""
    if status == "ok":
        status_class = "status-ok"
    elif status == "warning":
        status_class = "status-warning"
    elif status == "error":
        status_class = "status-error"

    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {status_class}">{value}</div>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main application."""

    # Sidebar - configuration
    with st.sidebar:
        # Brand header
        st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="margin: 0; font-size: 1.5rem;">AUDITSEO</h1>
            <p style="color: #94a3b8; font-size: 0.875rem; margin: 0;">Tool di analisi SEO</p>
        </div>
        """, unsafe_allow_html=True)

        # URL input section
        st.markdown('<p class="section-label">URL SITO</p>', unsafe_allow_html=True)
        url = st.text_input(
            "URL del sito",
            placeholder="https://www.esempio.it",
            help="Inserire l'URL completo del sito da analizzare",
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Settings section
        st.markdown('<p class="section-label">IMPOSTAZIONI</p>', unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown('<span style="font-size: 0.875rem;">Max pagine</span>', unsafe_allow_html=True)
        with col2:
            max_pages = st.number_input(
                "Limite pagine",
                min_value=0,
                max_value=10000,
                value=100,
                help="0 = nessun limite",
                label_visibility="collapsed"
            )

        screenshots = st.checkbox(
            "Cattura screenshot",
            value=True,
            help="Richiede Playwright installato"
        )

        with st.expander("Opzioni avanzate"):
            similarity = st.slider(
                "Soglia similarita duplicati",
                min_value=0.5,
                max_value=1.0,
                value=0.85,
                step=0.05
            )

            concurrency = st.number_input(
                "Richieste parallele",
                min_value=1,
                max_value=50,
                value=10
            )

            delay = st.number_input(
                "Delay tra richieste (ms)",
                min_value=0,
                max_value=1000,
                value=100
            )

        # AI Configuration Section
        if AI_AVAILABLE:
            st.markdown("---")
            st.markdown('<p class="section-label">INTELLIGENZA ARTIFICIALE</p>', unsafe_allow_html=True)

            use_ai = st.checkbox(
                "Attiva AI",
                value=st.session_state.get('use_ai', False),
                help="Genera testi usando Claude, OpenAI o Gemini"
            )
            st.session_state['use_ai'] = use_ai

            if use_ai:
                st.caption("Priorita: Claude, OpenAI, Gemini, Template")

                # Claude Configuration
                with st.expander("Claude (Anthropic)", expanded=False):
                    claude_key = st.text_input(
                        "API Key",
                        type="password",
                        value=st.session_state.get('claude_api_key', ''),
                        help="Ottieni la chiave su console.anthropic.com",
                        key="claude_key_input"
                    )
                    st.session_state['claude_api_key'] = claude_key

                    col1, col2 = st.columns([2, 1])
                    with col1:
                        if claude_key:
                            # Model selection
                            claude_models = [(m[0], m[1]) for m in CLAUDE_MODELS]
                            model_options = [m[1] for m in claude_models]
                            model_ids = [m[0] for m in claude_models]

                            current_model = st.session_state.get('claude_model', model_ids[0])
                            current_idx = model_ids.index(current_model) if current_model in model_ids else 0

                            selected_model = st.selectbox(
                                "Modello",
                                options=model_options,
                                index=current_idx,
                                key="claude_model_select",
                                disabled=not st.session_state.get('claude_validated', False)
                            )
                            st.session_state['claude_model'] = model_ids[model_options.index(selected_model)]

                    with col2:
                        if st.button("Verifica", key="validate_claude"):
                            with st.spinner("Verifica..."):
                                result = validate_claude_key(claude_key)
                                st.session_state['claude_validated'] = result.valid
                                st.session_state['claude_validation_msg'] = result.message

                    # Show validation status
                    if 'claude_validation_msg' in st.session_state:
                        if st.session_state.get('claude_validated', False):
                            st.success(st.session_state['claude_validation_msg'])
                        else:
                            st.error(st.session_state['claude_validation_msg'])

                # OpenAI Configuration
                with st.expander("OpenAI", expanded=False):
                    openai_key = st.text_input(
                        "API Key",
                        type="password",
                        value=st.session_state.get('openai_api_key', ''),
                        help="Ottieni la chiave su platform.openai.com",
                        key="openai_key_input"
                    )
                    st.session_state['openai_api_key'] = openai_key

                    col1, col2 = st.columns([2, 1])
                    with col1:
                        if openai_key:
                            openai_models = [(m[0], m[1]) for m in OPENAI_MODELS]
                            model_options = [m[1] for m in openai_models]
                            model_ids = [m[0] for m in openai_models]

                            current_model = st.session_state.get('openai_model', model_ids[0])
                            current_idx = model_ids.index(current_model) if current_model in model_ids else 0

                            selected_model = st.selectbox(
                                "Modello",
                                options=model_options,
                                index=current_idx,
                                key="openai_model_select",
                                disabled=not st.session_state.get('openai_validated', False)
                            )
                            st.session_state['openai_model'] = model_ids[model_options.index(selected_model)]

                    with col2:
                        if st.button("Verifica", key="validate_openai"):
                            with st.spinner("Verifica..."):
                                result = validate_openai_key(openai_key)
                                st.session_state['openai_validated'] = result.valid
                                st.session_state['openai_validation_msg'] = result.message

                    if 'openai_validation_msg' in st.session_state:
                        if st.session_state.get('openai_validated', False):
                            st.success(st.session_state['openai_validation_msg'])
                        else:
                            st.error(st.session_state['openai_validation_msg'])

                # Gemini Configuration
                with st.expander("Google Gemini", expanded=False):
                    gemini_key = st.text_input(
                        "API Key",
                        type="password",
                        value=st.session_state.get('gemini_api_key', ''),
                        help="Ottieni la chiave su aistudio.google.com",
                        key="gemini_key_input"
                    )
                    st.session_state['gemini_api_key'] = gemini_key

                    col1, col2 = st.columns([2, 1])
                    with col1:
                        if gemini_key:
                            gemini_models = [(m[0], m[1]) for m in GEMINI_MODELS]
                            model_options = [m[1] for m in gemini_models]
                            model_ids = [m[0] for m in gemini_models]

                            current_model = st.session_state.get('gemini_model', model_ids[0])
                            current_idx = model_ids.index(current_model) if current_model in model_ids else 0

                            selected_model = st.selectbox(
                                "Modello",
                                options=model_options,
                                index=current_idx,
                                key="gemini_model_select",
                                disabled=not st.session_state.get('gemini_validated', False)
                            )
                            st.session_state['gemini_model'] = model_ids[model_options.index(selected_model)]

                    with col2:
                        if st.button("Verifica", key="validate_gemini"):
                            with st.spinner("Verifica..."):
                                result = validate_gemini_key(gemini_key)
                                st.session_state['gemini_validated'] = result.valid
                                st.session_state['gemini_validation_msg'] = result.message

                    if 'gemini_validation_msg' in st.session_state:
                        if st.session_state.get('gemini_validated', False):
                            st.success(st.session_state['gemini_validation_msg'])
                        else:
                            st.error(st.session_state['gemini_validation_msg'])

                # Show provider summary
                st.markdown("---")
                st.markdown('<p class="section-label">STATO PROVIDER</p>', unsafe_allow_html=True)

                claude_status = "Attivo" if st.session_state.get('claude_validated', False) else "---"
                openai_status = "Attivo" if st.session_state.get('openai_validated', False) else "---"
                gemini_status = "Attivo" if st.session_state.get('gemini_validated', False) else "---"

                st.markdown(f"""
                <div style="font-size: 0.8rem; color: #64748b;">
                    <div style="display: flex; justify-content: space-between; padding: 0.25rem 0;">
                        <span>Claude</span>
                        <span style="color: {'#10b981' if claude_status == 'Attivo' else '#94a3b8'};">{claude_status}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 0.25rem 0;">
                        <span>OpenAI</span>
                        <span style="color: {'#10b981' if openai_status == 'Attivo' else '#94a3b8'};">{openai_status}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 0.25rem 0;">
                        <span>Gemini</span>
                        <span style="color: {'#10b981' if gemini_status == 'Attivo' else '#94a3b8'};">{gemini_status}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 0.25rem 0;">
                        <span>Template</span>
                        <span style="color: #10b981;">Fallback</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Warning if no provider validated
                has_validated = any([
                    st.session_state.get('claude_validated', False),
                    st.session_state.get('openai_validated', False),
                    st.session_state.get('gemini_validated', False)
                ])
                if not has_validated:
                    st.warning("Nessun provider AI validato. Verra usato il template.")

        st.markdown("---")

        run_button = st.button("AVVIA AUDIT", type="primary", use_container_width=True)

    # Main content area
    if 'results' not in st.session_state:
        st.session_state.results = None

    if run_button and url:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Progress container
        progress_container = st.container()

        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(message, progress):
                status_text.text(message)
                progress_bar.progress(progress)

            try:
                # Get AI config if enabled
                ai_config = get_ai_config_from_session() if AI_AVAILABLE else None

                with st.spinner("Elaborazione in corso..."):
                    results = run_audit(
                        url=url,
                        max_pages=max_pages,
                        screenshots=screenshots,
                        similarity=similarity,
                        concurrency=concurrency,
                        delay=delay,
                        progress_callback=update_progress,
                        ai_config=ai_config
                    )
                    st.session_state.results = results
                    # Store audit ID for feedback
                    st.session_state.audit_id = f"audit_{results['domain'].replace('.', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            except Exception as e:
                st.error(f"Errore durante l'audit: {str(e)}")
                st.session_state.results = None

    # Display results
    if st.session_state.results:
        results = st.session_state.results
        audit_date = datetime.now().strftime("%d %b %Y")

        # Results header
        total_pages = results['summary'].get('total_pages', 0)
        total_urls = results['summary'].get('total_urls_crawled', total_pages)
        total_redirects = results['summary'].get('total_redirects', 0)
        total_errors = results['summary'].get('total_errors', 0)

        meta_text = f"{results['domain']} · {total_pages} pagine analizzate"
        if total_redirects > 0:
            meta_text += f" · {total_redirects} redirect"
        if total_errors > 0:
            meta_text += f" · {total_errors} errori"
        meta_text += f" · {audit_date}"

        st.markdown(f"""
        <div class="results-header">
            <h2 style="margin: 0 !important;">RISULTATI AUDIT</h2>
            <p class="results-meta">{meta_text}</p>
        </div>
        """, unsafe_allow_html=True)

        # AI Status notification (cleaned up, no emojis)
        ai_status = results.get('ai_status', {})
        if ai_status:
            ai_enabled = ai_status.get('ai_enabled', False)
            ai_available = ai_status.get('ai_available', False)
            success_count = ai_status.get('success_count', 0)
            failure_count = ai_status.get('failure_count', 0)
            failures = ai_status.get('failures', [])

            if not ai_enabled:
                st.warning(
                    "**AI non attivata** - I testi sono stati generati usando template statici. "
                    "Configura un provider AI nella sidebar per analisi personalizzate."
                )
            elif not ai_available:
                st.error(
                    "**AI non disponibile** - Nessun provider configurato correttamente. "
                    "Verifica le API key. I testi sono stati generati con template."
                )
            elif failure_count > 0:
                with st.expander(f"Attenzione: {failure_count} sezioni generate con template", expanded=True):
                    st.markdown("L'AI non e riuscita a generare alcune sezioni:")
                    for failure in failures:
                        st.markdown(f"- **{failure.get('section', 'N/A')}**: {failure.get('reason', 'Errore sconosciuto')}")
                    st.markdown("---")
                    st.markdown(f"Sezioni AI: **{success_count}** | Template: **{failure_count}**")
            elif success_count > 0:
                st.success(f"**AI attiva** - {success_count} sezioni generate con intelligenza artificiale.")
        else:
            st.info(
                "**Modalita template** - I testi sono stati generati usando template predefiniti. "
                "Attiva l'AI nella sidebar per analisi dettagliate."
            )

        # Download buttons bar
        st.markdown('<p class="section-label" style="margin-top: 1.5rem;">ESPORTA</p>', unsafe_allow_html=True)
        col_dl1, col_dl2, col_dl3, col_dl_spacer = st.columns([1, 1, 1, 2])

        with col_dl1:
            if 'markdown' in results['reports']:
                md_content = results['reports']['markdown']['content']
                st.download_button(
                    label="Markdown",
                    data=md_content,
                    file_name=f"audit_{results['domain'].replace('.', '_')}.md",
                    mime="text/markdown"
                )

        with col_dl2:
            if 'docx' in results['reports']:
                docx_path = results['reports']['docx']['path']
                if os.path.exists(docx_path):
                    with open(docx_path, 'rb') as f:
                        st.download_button(
                            label="Word",
                            data=f.read(),
                            file_name=f"Audit SEO - {results['site_name']}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )

        with col_dl3:
            if 'json' in results['reports']:
                json_data = json.dumps(results['reports']['json']['data'], indent=2, ensure_ascii=False)
                st.download_button(
                    label="JSON",
                    data=json_data,
                    file_name=f"audit_{results['domain'].replace('.', '_')}_data.json",
                    mime="application/json"
                )

        st.markdown("---")

        # Crawl Overview metrics
        st.markdown('<p class="section-label">PANORAMICA CRAWL</p>', unsafe_allow_html=True)

        def render_metric_card(value, label, status="info"):
            status_class = f"metric-card-{status}"
            return f"""
            <div class="metric-card {status_class}">
                <div class="metric-value">{value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """

        col_o1, col_o2, col_o3, col_o4 = st.columns(4)

        with col_o1:
            val = results['summary'].get('total_urls_crawled', 0)
            st.markdown(render_metric_card(val, "URL Totali", "info"), unsafe_allow_html=True)

        with col_o2:
            val = results['summary'].get('total_pages', 0)
            st.markdown(render_metric_card(val, "Pagine Analizzate", "success"), unsafe_allow_html=True)

        with col_o3:
            val = results['summary'].get('total_redirects', 0)
            status = "success" if val == 0 else "warning"
            st.markdown(render_metric_card(val, "Redirect", status), unsafe_allow_html=True)

        with col_o4:
            val = results['summary'].get('total_errors', 0)
            status = "success" if val == 0 else "error"
            st.markdown(render_metric_card(val, "Errori", status), unsafe_allow_html=True)

        st.markdown("---")

        # SEO Quality metrics
        st.markdown('<p class="section-label">METRICHE QUALITÀ SEO</p>', unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            val = results['summary'].get('without_title', 0)
            status = "success" if val == 0 else "error"
            st.markdown(render_metric_card(val, "Senza Title", status), unsafe_allow_html=True)

        with col2:
            val = results['summary'].get('without_h1', 0)
            status = "success" if val == 0 else "warning" if val < 5 else "error"
            st.markdown(render_metric_card(val, "Senza H1", status), unsafe_allow_html=True)

        with col3:
            val = results['summary'].get('canonical_missing', 0)
            status = "success" if val == 0 else "error"
            st.markdown(render_metric_card(val, "Senza Canonical", status), unsafe_allow_html=True)

        with col4:
            val = results['summary'].get('duplicates', 0)
            status = "success" if val == 0 else "warning"
            st.markdown(render_metric_card(val, "Duplicati", status), unsafe_allow_html=True)

        col5, col6, col7, col8 = st.columns(4)

        with col5:
            val = results['summary'].get('without_description', 0)
            status = "success" if val == 0 else "warning" if val < 5 else "error"
            st.markdown(render_metric_card(val, "Senza Description", status), unsafe_allow_html=True)

        with col6:
            val = results['summary'].get('errors_404', 0)
            status = "success" if val == 0 else "error"
            st.markdown(render_metric_card(val, "Errori 404", status), unsafe_allow_html=True)

        with col7:
            val = results['summary'].get('orphan_pages', 0)
            status = "success" if val == 0 else "warning"
            st.markdown(render_metric_card(val, "Pagine Orfane", status), unsafe_allow_html=True)

        with col8:
            val = results['summary'].get('pages_with_schema', 0)
            total = results['summary'].get('total_pages', 1)
            pct = int(val / total * 100) if total > 0 else 0
            status = "success" if pct >= 80 else "warning" if pct >= 50 else "info"
            st.markdown(render_metric_card(f"{pct}%", "Con Schema.org", status), unsafe_allow_html=True)

        st.markdown("---")

        # Pages list section
        pages_list = results.get('pages_list', [])
        if pages_list:
            st.markdown('<p class="section-label">PAGINE ANALIZZATE</p>', unsafe_allow_html=True)

            # Filter controls
            col_filter1, col_filter2, col_filter3 = st.columns([2, 1, 1])
            with col_filter1:
                search_term = st.text_input(
                    "Cerca URL",
                    placeholder="Filtra per URL...",
                    key="page_search",
                    label_visibility="collapsed"
                )
            with col_filter2:
                status_filter = st.selectbox(
                    "Status",
                    options=["Tutti", "200 OK", "3xx Redirect", "4xx Errori", "5xx Server"],
                    key="status_filter",
                    label_visibility="collapsed"
                )
            with col_filter3:
                sort_by = st.selectbox(
                    "Ordina per",
                    options=["URL", "Status", "Depth", "Words", "Load (ms)"],
                    key="sort_by",
                    label_visibility="collapsed"
                )

            # Apply filters
            df = pd.DataFrame(pages_list)

            if search_term:
                df = df[df['URL'].str.contains(search_term, case=False, na=False)]

            if status_filter == "200 OK":
                df = df[df['Status'] == 200]
            elif status_filter == "3xx Redirect":
                df = df[(df['Status'] >= 300) & (df['Status'] < 400)]
            elif status_filter == "4xx Errori":
                df = df[(df['Status'] >= 400) & (df['Status'] < 500)]
            elif status_filter == "5xx Server":
                df = df[df['Status'] >= 500]

            # Sort
            if sort_by in df.columns:
                ascending = sort_by not in ["Words", "Load (ms)"]
                df = df.sort_values(by=sort_by, ascending=ascending)

            # Display count
            st.caption(f"Mostrando {len(df)} di {len(pages_list)} pagine")

            # Display dataframe with styling
            with st.expander(f"Visualizza elenco pagine ({len(df)} risultati)", expanded=False):
                # Style the dataframe
                def style_status(val):
                    if val == 200:
                        return 'color: #10b981'
                    elif 300 <= val < 400:
                        return 'color: #f59e0b'
                    elif val >= 400:
                        return 'color: #ef4444'
                    return ''

                styled_df = df.style.applymap(style_status, subset=['Status'])
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    height=400,
                    column_config={
                        "URL": st.column_config.TextColumn("URL", width="large"),
                        "Status": st.column_config.NumberColumn("Status", width="small"),
                        "Title": st.column_config.TextColumn("Title", width="medium"),
                        "H1": st.column_config.TextColumn("H1", width="medium"),
                        "Depth": st.column_config.NumberColumn("Depth", width="small"),
                        "Words": st.column_config.NumberColumn("Words", width="small"),
                        "Load (ms)": st.column_config.NumberColumn("Load (ms)", width="small"),
                    }
                )

            # Download CSV button
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="Esporta CSV",
                data=csv_data,
                file_name=f"pages_{results['domain'].replace('.', '_')}.csv",
                mime="text/csv"
            )

        st.markdown("---")

        # Strategic Linking Analysis section
        strategic_data = results['stages'].get('analysis', {}).get('strategic_linking', {})
        if strategic_data and 'error' not in strategic_data:
            st.markdown('<p class="section-label">LINKING STRATEGICO</p>', unsafe_allow_html=True)

            # Score and classification method
            score = strategic_data.get('strategic_linking_score', 0)
            method = strategic_data.get('classification_method', 'heuristic')
            score_color = "#10b981" if score >= 70 else "#f59e0b" if score >= 40 else "#ef4444"

            col_score, col_method = st.columns([1, 2])
            with col_score:
                st.markdown(f"""
                <div class="metric-card metric-card-{'success' if score >= 70 else 'warning' if score >= 40 else 'error'}">
                    <div class="metric-value" style="color: {score_color};">{score:.0f}</div>
                    <div class="metric-label">Score Strategico</div>
                </div>
                """, unsafe_allow_html=True)
            with col_method:
                st.caption(f"Classificazione: {method.upper()}")
                dist = strategic_data.get('page_type_distribution', {})
                st.caption(f"Trans: {dist.get('transactional', 0)} | Info: {dist.get('informational', 0)} | Nav: {dist.get('navigational', 0)}")

            # Link Flow Matrix
            with st.expander("Matrice Flusso Link", expanded=False):
                st.markdown("**Come le diverse tipologie di pagine si linkano tra loro:**")
                flow_matrix = strategic_data.get('link_flow_matrix', {})
                if flow_matrix:
                    # Create DataFrame for flow matrix
                    flow_df = pd.DataFrame(flow_matrix).T
                    flow_df.index.name = "Da / Verso"
                    st.dataframe(flow_df, use_container_width=True)

                    # Key metrics
                    info_to_trans = strategic_data.get('info_to_trans_count', 0)
                    trans_to_info = strategic_data.get('trans_to_info_count', 0)
                    ratio = strategic_data.get('info_to_trans_ratio', 0)

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Info -> Trans", info_to_trans)
                    with col2:
                        st.metric("Trans -> Info", trans_to_info)
                    with col3:
                        st.metric("Ratio Info->Trans", f"{ratio*100:.1f}%")

            # Hub Pages
            hub_pages = strategic_data.get('hub_pages', [])
            if hub_pages:
                with st.expander(f"Hub Pages ({len(hub_pages)} identificate)", expanded=False):
                    st.markdown("**Pagine che distribuiscono maggiore link equity:**")
                    hub_df = pd.DataFrame([
                        {
                            'URL': h['url'][:60] + '...' if len(h['url']) > 60 else h['url'],
                            'Tipo': h['type'].title(),
                            'Link Out': h['outgoing'],
                            'Link In': h['incoming'],
                            '-> Trans': h['to_trans'],
                            'Hub Score': f"{h['hub_score']:.1f}"
                        }
                        for h in hub_pages[:10]
                    ])
                    st.dataframe(hub_df, use_container_width=True, hide_index=True)

            # Isolated Pages - Critical Issues
            isolated_trans = strategic_data.get('isolated_transactional', [])
            isolated_info = strategic_data.get('isolated_informational', [])

            if isolated_trans:
                with st.expander(f"Pagine Transazionali Isolate ({len(isolated_trans)})", expanded=True):
                    st.markdown("""
                    <span class="badge badge-critical">Critico</span>
                    <p style="margin-top: 0.5rem;">Pagine commerciali che non ricevono supporto da contenuti informativi:</p>
                    """, unsafe_allow_html=True)
                    for page in isolated_trans[:10]:
                        st.code(page['url'], language=None)
                    if len(isolated_trans) > 10:
                        st.caption(f"... e altre {len(isolated_trans) - 10} pagine")
                    st.markdown("**Raccomandazione:** Creare guide, blog post o FAQ che linkano a queste pagine.")

            if isolated_info:
                with st.expander(f"Pagine Informative non Valorizzanti ({len(isolated_info)})", expanded=False):
                    st.markdown("""
                    <span class="badge badge-warning">Attenzione</span>
                    <p style="margin-top: 0.5rem;">Contenuti informativi che non linkano a pagine transazionali:</p>
                    """, unsafe_allow_html=True)
                    for page in isolated_info[:10]:
                        st.code(page['url'], language=None)
                    if len(isolated_info) > 10:
                        st.caption(f"... e altre {len(isolated_info) - 10} pagine")
                    st.markdown("**Raccomandazione:** Aggiungere CTA e link contestuali verso prodotti/servizi.")

            # Issues Summary
            issues = strategic_data.get('issues', [])
            if issues:
                with st.expander("Problemi e Raccomandazioni", expanded=False):
                    for issue in issues:
                        severity = issue.get('severity', 'info')
                        badge_class = 'badge-critical' if severity == 'critical' else 'badge-warning' if severity == 'warning' else 'badge-info'
                        st.markdown(f"""
                        <div style="margin-bottom: 1rem; padding: 1rem; background: #f8fafc; border-radius: 6px;">
                            <span class="badge {badge_class}">{severity.title()}</span>
                            <strong style="margin-left: 0.5rem;">{issue.get('title', '')}</strong>
                            <p style="margin: 0.5rem 0; color: #64748b;">{issue.get('description', '')}</p>
                            <p style="margin: 0; font-size: 0.875rem;"><strong>Azione:</strong> {issue.get('recommendation', '')}</p>
                        </div>
                        """, unsafe_allow_html=True)

        st.markdown("---")

        # Screenshots section
        screenshots = results.get('screenshots', {})
        if screenshots:
            st.markdown('<p class="section-label">SCREENSHOT</p>', unsafe_allow_html=True)
            cols = st.columns(2)
            col_idx = 0
            for name, path in screenshots.items():
                if os.path.exists(path):
                    with cols[col_idx % 2]:
                        st.image(path, caption=name.replace('_', ' ').title(), use_container_width=True)
                    col_idx += 1
            st.markdown("---")

        # Detailed sections with generated narratives
        st.markdown('<p class="section-label">ANALISI DETTAGLIATA</p>', unsafe_allow_html=True)

        if AI_AVAILABLE and st.session_state.get('use_ai', False):
            st.caption("Ogni sezione mostra il testo generato. Vai nella tab Feedback per valutarlo.")

        analysis = results['stages'].get('analysis', {})
        narratives = results.get('narratives', {})

        # Define section order and grouping
        architecture_sections = ['alberatura', 'canonical', 'hreflang', 'url']
        content_sections = ['title', 'description', 'headings', 'images', 'linking']
        technical_sections = ['performance', 'sitemap', 'robots', 'https', 'errors', 'structured_data']

        # Architecture Group
        st.markdown("### Architettura")
        for section_key in architecture_sections:
            if section_key in narratives:
                with st.expander(f"{narratives[section_key].get('title', section_key.title())}", expanded=False):
                    render_narrative_section(
                        section_key,
                        narratives[section_key],
                        narratives[section_key].get('data', {})
                    )

        # Content Group
        st.markdown("### Contenuti")
        for section_key in content_sections:
            if section_key in narratives:
                with st.expander(f"{narratives[section_key].get('title', section_key.title())}", expanded=False):
                    render_narrative_section(
                        section_key,
                        narratives[section_key],
                        narratives[section_key].get('data', {})
                    )

        # Technical Group
        st.markdown("### Tecnico")
        for section_key in technical_sections:
            if section_key in narratives:
                with st.expander(f"{narratives[section_key].get('title', section_key.title())}", expanded=False):
                    render_narrative_section(
                        section_key,
                        narratives[section_key],
                        narratives[section_key].get('data', {})
                    )

    elif not run_button:
        # Initial state - clean welcome
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1rem;">
            <h1 style="font-size: 2.5rem; margin-bottom: 0.5rem;">AuditSEO Tool</h1>
            <p style="color: #64748b; font-size: 1rem; margin-bottom: 2rem;">Analisi SEO professionale con report in formato Markdown e DOCX</p>
        </div>
        """, unsafe_allow_html=True)

        st.info("Inserisci l'URL del sito nella barra laterale e clicca AVVIA AUDIT per iniziare.")

        st.markdown("### Funzionalita")
        st.markdown("""
- **Crawling completo** del sito con gestione asincrona
- **Analisi architettura**: alberatura, canonical, hreflang, URL
- **Analisi contenuti**: title, description, heading, immagini
- **Rilevamento duplicati** con algoritmo SimHash
- **Analisi tecnica**: status code, redirect, HTTPS, robots.txt
- **Dati strutturati**: verifica Schema.org
- **Report professionali** in formato Markdown e DOCX
        """)


if __name__ == "__main__":
    main()
