"""DOCX report generator."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import logging

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT

from .narrative import NarrativeGenerator, NarrativeSection

logger = logging.getLogger(__name__)


class DocxReporter:
    """Generator for DOCX audit reports."""

    def __init__(
        self,
        site_name: str,
        site_url: str,
        output_dir: Path = None,
        ai_config: Optional["AIConfig"] = None
    ):
        """Initialize reporter.

        Args:
            site_name: Name of the site
            site_url: URL of the site
            output_dir: Output directory for report
            ai_config: Optional AI configuration for intelligent generation
        """
        self.site_name = site_name
        self.site_url = site_url
        self.output_dir = output_dir or Path(".")
        self.narrative = NarrativeGenerator(site_name, site_url)
        self.doc = None

        # AI integration
        self.ai_config = ai_config
        self._ai_orchestrator = None
        self._generation_results = {}  # Track which provider generated each section

    def _get_ai_orchestrator(self):
        """Lazy initialization of AI orchestrator."""
        if self._ai_orchestrator is None and self.ai_config is not None:
            try:
                from ..ai.orchestrator import AIOrchestrator
                from ..ai.feedback.storage import FeedbackStorage

                feedback_storage = FeedbackStorage()
                self._ai_orchestrator = AIOrchestrator(
                    config=self.ai_config,
                    site_name=self.site_name,
                    site_url=self.site_url,
                    feedback_storage=feedback_storage
                )
            except Exception as e:
                logger.warning(f"Failed to initialize AI orchestrator: {e}")
                self._ai_orchestrator = None
        return self._ai_orchestrator

    def _generate_section_with_ai(
        self,
        section_key: str,
        section_data: Dict[str, Any]
    ) -> NarrativeSection:
        """Generate section using AI with fallback to template.

        Args:
            section_key: Key identifying the section
            section_data: Analysis data for the section

        Returns:
            NarrativeSection with generated content
        """
        orchestrator = self._get_ai_orchestrator()
        logger.info(f"[AI] Section {section_key}: orchestrator={'available' if orchestrator else 'None'}")

        if orchestrator is not None:
            try:
                result = orchestrator.generate_section_safe(section_key, section_data)
                logger.info(f"[AI] Section {section_key}: source={result.source.value}, model={result.model}, success={result.success}")

                # Track which provider was used
                self._generation_results[section_key] = {
                    "source": result.source.value,
                    "model": result.model,
                    "success": result.success
                }

                # Only return AI-generated content if it's not from template fallback
                if result.success and result.current_situation and result.source.value != "template":
                    logger.info(f"[AI] Section {section_key}: Using AI-generated content")
                    return NarrativeSection(
                        title=section_key.title(),
                        premise=self.narrative.get_premise(section_key),
                        current_situation=result.current_situation,
                        improvements=result.improvements
                    )
                else:
                    logger.warning(f"[AI] Section {section_key}: AI returned template fallback")
            except Exception as e:
                logger.warning(f"AI generation failed for {section_key}: {e}")

        # Fallback to template
        self._generation_results[section_key] = {
            "source": "template",
            "model": None,
            "success": True
        }
        logger.info(f"[AI] Section {section_key}: Using template fallback")
        return None  # Signal to use template method

    def get_generation_results(self) -> Dict[str, Dict[str, Any]]:
        """Get information about which provider generated each section."""
        return self._generation_results.copy()

    def get_ai_status(self) -> Dict[str, Any]:
        """Get AI usage status for reporting to user.

        Returns:
            Dict with ai_used, ai_available, failures, etc.
        """
        orchestrator = self._get_ai_orchestrator()
        if orchestrator is not None:
            return orchestrator.get_ai_status_summary()
        return {
            "ai_enabled": False,
            "ai_available": False,
            "success_count": 0,
            "failure_count": 0,
            "template_fallbacks": len(self._generation_results),
            "failures": [],
            "providers_tried": [],
            "reason": "AI non configurata" if self.ai_config is None else "Orchestrator non inizializzato"
        }

    def _setup_document(self):
        """Setup document with styles."""
        self.doc = Document()

        # Set up styles
        styles = self.doc.styles

        # Modify Heading 1
        h1_style = styles['Heading 1']
        h1_style.font.size = Pt(18)
        h1_style.font.bold = True
        h1_style.font.color.rgb = RGBColor(0, 51, 102)

        # Modify Heading 2
        h2_style = styles['Heading 2']
        h2_style.font.size = Pt(14)
        h2_style.font.bold = True
        h2_style.font.color.rgb = RGBColor(0, 51, 102)

        # Modify Heading 3
        h3_style = styles['Heading 3']
        h3_style.font.size = Pt(12)
        h3_style.font.bold = True

        # Normal text
        normal_style = styles['Normal']
        normal_style.font.size = Pt(11)
        normal_style.font.name = 'Calibri'

    def _add_title_page(self):
        """Add title page."""
        # Title
        title = self.doc.add_heading(f'Audit SEO', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Site name
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(self.site_name)
        run.font.size = Pt(24)
        run.bold = True

        # URL
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(self.site_url)
        run.font.size = Pt(14)

        # Date
        self.doc.add_paragraph()
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(datetime.now().strftime('%d/%m/%Y'))
        run.font.size = Pt(12)

        self.doc.add_page_break()

    def _add_toc(self):
        """Add table of contents placeholder."""
        self.doc.add_heading('INDICE', 1)
        p = self.doc.add_paragraph()
        p.add_run('Indice generato automaticamente da Word')
        p.italic = True
        self.doc.add_page_break()

    def _add_section(self, number: str, title: str, premise: str,
                     situation: str, improvements: str):
        """Add a standard section."""
        self.doc.add_heading(f'{number} {title}', 2)

        # Premise
        p = self.doc.add_paragraph()
        run = p.add_run('Premessa')
        run.bold = True
        self.doc.add_paragraph(premise)

        # Situation
        p = self.doc.add_paragraph()
        run = p.add_run('Situazione attuale')
        run.bold = True
        self.doc.add_paragraph(situation)

        # Improvements
        p = self.doc.add_paragraph()
        run = p.add_run('Come migliorare')
        run.bold = True
        self.doc.add_paragraph(improvements)

    def _add_narrative_section(self, number: str, section: NarrativeSection):
        """Add a NarrativeSection to document."""
        self._add_section(
            number,
            section.title,
            section.premise,
            section.current_situation,
            section.improvements
        )

    def _add_examples_header(self, title: str):
        """Add a header for examples section."""
        p = self.doc.add_paragraph()
        run = p.add_run(title)
        run.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0, 51, 102)

    def _add_url_list(self, urls: List[str], max_items: int = 10, prefix: str = ""):
        """Add a list of URLs to the document.

        Args:
            urls: List of URLs to display
            max_items: Maximum number of items to show
            prefix: Optional prefix text for each item
        """
        if not urls:
            return

        for url in urls[:max_items]:
            p = self.doc.add_paragraph(style='List Bullet')
            if prefix:
                run = p.add_run(f"{prefix}: ")
                run.bold = True
            run = p.add_run(str(url))
            run.font.size = Pt(9)
            run.font.name = 'Consolas'

        if len(urls) > max_items:
            p = self.doc.add_paragraph()
            p.add_run(f"... e altri {len(urls) - max_items} elementi").italic = True

    def _add_examples_table(self, headers: List[str], rows: List[List[str]], max_rows: int = 10):
        """Add a table with examples.

        Args:
            headers: Column headers
            rows: List of row data
            max_rows: Maximum rows to display
        """
        if not rows:
            return

        table = self.doc.add_table(rows=1, cols=len(headers))
        table.style = 'Table Grid'

        # Header
        header_cells = table.rows[0].cells
        for i, header in enumerate(headers):
            header_cells[i].text = header
            header_cells[i].paragraphs[0].runs[0].bold = True
            header_cells[i].paragraphs[0].runs[0].font.size = Pt(9)

        # Data rows
        for row_data in rows[:max_rows]:
            row_cells = table.add_row().cells
            for i, cell_data in enumerate(row_data):
                row_cells[i].text = str(cell_data)[:100]  # Truncate long text
                row_cells[i].paragraphs[0].runs[0].font.size = Pt(8)

        if len(rows) > max_rows:
            p = self.doc.add_paragraph()
            p.add_run(f"... e altri {len(rows) - max_rows} elementi").italic = True

        self.doc.add_paragraph()  # Spacing

    def _add_section_with_examples(
        self,
        number: str,
        section: NarrativeSection,
        data: Dict[str, Any],
        section_key: str
    ):
        """Add a section with narrative text AND concrete examples."""
        # Add the narrative section first
        self._add_narrative_section(number, section)

        # Add examples based on section type
        self._add_section_examples(section_key, data)

    def _add_section_examples(self, section_key: str, data: Dict[str, Any]):
        """Add examples specific to each section type."""

        if section_key == 'alberatura':
            # Orphan pages
            orphans = data.get('orphan_pages', [])
            if orphans and isinstance(orphans, list) and len(orphans) > 0:
                self._add_examples_header("Pagine orfane rilevate:")
                self._add_url_list(orphans, max_items=10)

            # Deep pages
            deep_pages = data.get('deep_pages', [])
            if deep_pages and isinstance(deep_pages, list) and len(deep_pages) > 0:
                self._add_examples_header("Pagine troppo profonde (>3 click dalla home):")
                self._add_url_list(deep_pages, max_items=10)

            # Depth distribution as mini-table
            depth_dist = data.get('depth_distribution', {})
            if depth_dist and isinstance(depth_dist, dict):
                self._add_examples_header("Distribuzione pagine per livello di profondità:")
                rows = [[f"Livello {d}", str(c)] for d, c in sorted(depth_dist.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0)]
                self._add_examples_table(["Profondità", "N. Pagine"], rows)

        elif section_key == 'canonical':
            canonical_issues = data.get('canonical_issues', {})
            if not isinstance(canonical_issues, dict):
                canonical_issues = {}

            # Missing canonical
            missing = canonical_issues.get('missing_list', [])
            if missing and isinstance(missing, list):
                self._add_examples_header("Pagine senza tag canonical:")
                self._add_url_list(missing, max_items=10)

            # Mismatched canonical
            mismatches = canonical_issues.get('mismatches_list', [])
            if mismatches and isinstance(mismatches, list):
                self._add_examples_header("Pagine con canonical non corrispondente:")
                rows = []
                for item in mismatches[:10]:
                    if isinstance(item, dict):
                        rows.append([str(item.get('url', 'N/A'))[:50], str(item.get('canonical', 'N/A'))[:50]])
                    else:
                        rows.append([str(item)[:50], ""])
                if rows:
                    self._add_examples_table(["URL Pagina", "Canonical impostato"], rows)

            # Duplicates
            dup_data = data.get('duplicates_data', {})
            if not isinstance(dup_data, dict):
                dup_data = {}
            dups = dup_data.get('duplicates', {})
            if not isinstance(dups, dict):
                dups = {}
            exact = dups.get('exact', 0) if isinstance(dups.get('exact', 0), int) else 0
            near = dups.get('near', 0) if isinstance(dups.get('near', 0), int) else 0
            if exact > 0 or near > 0:
                self._add_examples_header(f"Contenuti duplicati rilevati: {exact} esatti, {near} simili")

        elif section_key == 'hreflang':
            hreflang = data.get('hreflang', {})
            if not isinstance(hreflang, dict):
                hreflang = {}

            languages = hreflang.get('languages', [])
            if languages and isinstance(languages, list):
                self._add_examples_header(f"Lingue rilevate: {', '.join(str(l) for l in languages)}")

            non_recip = hreflang.get('non_reciprocal_list', [])
            if non_recip and isinstance(non_recip, list):
                self._add_examples_header("Hreflang non reciproci:")
                self._add_url_list(non_recip[:5], max_items=5)

        elif section_key == 'title':
            titles = data.get('titles', {})
            if not isinstance(titles, dict):
                titles = {}

            # Without title
            without = titles.get('without_title_list', [])
            if without and isinstance(without, list):
                self._add_examples_header("Pagine senza meta title:")
                self._add_url_list(without, max_items=10)

            # Duplicate titles
            duplicates = titles.get('duplicate_titles', {})
            if duplicates and isinstance(duplicates, dict):
                self._add_examples_header("Title duplicati:")
                rows = []
                for title, urls in list(duplicates.items())[:5]:
                    display_title = title[:60] + "..." if len(str(title)) > 60 else str(title)
                    url_count = len(urls) if isinstance(urls, (list, tuple)) else urls
                    rows.append([display_title, f"{url_count} pagine"])
                if rows:
                    self._add_examples_table(["Title", "Occorrenze"], rows)

            # Length issues
            long_titles = titles.get('long_titles_list', [])
            if long_titles and isinstance(long_titles, list):
                self._add_examples_header("Title troppo lunghi (>60 caratteri):")
                rows = []
                for item in long_titles[:5]:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        rows.append([str(item[0])[:50], str(item[1])])
                    elif isinstance(item, dict):
                        rows.append([str(item.get('url', 'N/A'))[:50], str(item.get('length', 0))])
                    else:
                        rows.append([str(item)[:50], ""])
                if rows:
                    self._add_examples_table(["URL", "Lunghezza"], rows)

        elif section_key == 'description':
            desc = data.get('descriptions', {})
            if not isinstance(desc, dict):
                desc = {}

            without = desc.get('without_description_list', [])
            if without and isinstance(without, list):
                self._add_examples_header("Pagine senza meta description:")
                self._add_url_list(without, max_items=10)

            duplicates = desc.get('duplicate_descriptions', {})
            if duplicates and isinstance(duplicates, dict):
                self._add_examples_header("Description duplicate:")
                rows = []
                for description, urls in list(duplicates.items())[:5]:
                    display_desc = str(description)[:60] + "..." if len(str(description)) > 60 else str(description)
                    url_count = len(urls) if isinstance(urls, (list, tuple)) else urls
                    rows.append([display_desc, f"{url_count} pagine"])
                if rows:
                    self._add_examples_table(["Description", "Occorrenze"], rows)

        elif section_key == 'headings':
            headings = data.get('headings', {})
            if not isinstance(headings, dict):
                headings = {}

            without_h1 = headings.get('without_h1_list', [])
            if without_h1 and isinstance(without_h1, list):
                self._add_examples_header("Pagine senza H1:")
                self._add_url_list(without_h1, max_items=10)

            multiple_h1 = headings.get('multiple_h1_list', [])
            if multiple_h1 and isinstance(multiple_h1, list):
                self._add_examples_header("Pagine con H1 multipli:")
                self._add_url_list(multiple_h1, max_items=5)

            duplicate_h1 = headings.get('duplicate_h1', {})
            if duplicate_h1 and isinstance(duplicate_h1, dict):
                self._add_examples_header("H1 duplicati:")
                rows = []
                for h1, urls in list(duplicate_h1.items())[:5]:
                    display_h1 = str(h1)[:60] + "..." if len(str(h1)) > 60 else str(h1)
                    url_count = len(urls) if isinstance(urls, (list, tuple)) else urls
                    rows.append([display_h1, f"{url_count} pagine"])
                if rows:
                    self._add_examples_table(["H1", "Occorrenze"], rows)

        elif section_key == 'images':
            images = data.get('images', {})
            if not isinstance(images, dict):
                images = {}

            # Summary
            total = images.get('total', 0) if isinstance(images.get('total', 0), int) else 0
            without_alt = images.get('without_alt', 0) if isinstance(images.get('without_alt', 0), int) else 0
            empty_alt = images.get('empty_alt', 0) if isinstance(images.get('empty_alt', 0), int) else 0
            if total > 0:
                self._add_examples_header(f"Riepilogo immagini: {total} totali, {without_alt} senza alt, {empty_alt} con alt vuoto")

            # Examples without alt
            without_list = images.get('without_alt_list', [])
            if without_list and isinstance(without_list, list):
                self._add_examples_header("Esempi di immagini senza attributo alt:")
                rows = []
                for item in without_list[:10]:
                    if isinstance(item, dict):
                        rows.append([str(item.get('page', 'N/A'))[:40], str(item.get('src', 'N/A'))[:40]])
                    else:
                        rows.append([str(item)[:40], ""])
                if rows:
                    self._add_examples_table(["Pagina", "Immagine"], rows)

        elif section_key == 'linking':
            linking = data.get('internal_linking', {})
            if not isinstance(linking, dict):
                linking = {}

            orphans = linking.get('orphan_pages_list', [])
            if orphans and isinstance(orphans, list):
                self._add_examples_header("Pagine senza link in ingresso (orfane):")
                self._add_url_list(orphans, max_items=10)

            many_links = linking.get('pages_with_many_links_list', [])
            if many_links and isinstance(many_links, list):
                self._add_examples_header("Pagine con troppi link (>100):")
                rows = []
                for item in many_links[:5]:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        rows.append([str(item[0])[:50], str(item[1])])
                    elif isinstance(item, dict):
                        rows.append([str(item.get('url', 'N/A'))[:50], str(item.get('count', 0))])
                    else:
                        rows.append([str(item)[:50], ""])
                if rows:
                    self._add_examples_table(["URL", "N. Link"], rows)

        elif section_key == 'performance':
            perf = data.get('performance', {})
            if not isinstance(perf, dict):
                perf = {}

            avg_time = perf.get('avg_load_time_ms', 0)
            if isinstance(avg_time, (int, float)) and avg_time > 0:
                self._add_examples_header(f"Tempo medio di caricamento: {avg_time/1000:.2f} secondi")

            slow_pages = perf.get('slow_pages_list', [])
            if slow_pages and isinstance(slow_pages, list):
                self._add_examples_header("Pagine lente (>3 secondi):")
                rows = []
                for item in slow_pages[:10]:
                    if isinstance(item, dict):
                        time_ms = item.get('time_ms', 0)
                        if isinstance(time_ms, (int, float)):
                            rows.append([str(item.get('url', 'N/A'))[:50], f"{time_ms/1000:.2f}s"])
                        else:
                            rows.append([str(item.get('url', 'N/A'))[:50], ""])
                    else:
                        rows.append([str(item)[:50], ""])
                if rows:
                    self._add_examples_table(["URL", "Tempo"], rows)

        elif section_key == 'structured_data':
            total = data.get('total_pages', 0) if isinstance(data.get('total_pages', 0), int) else 0
            with_schema = data.get('pages_with_schema', 0) if isinstance(data.get('pages_with_schema', 0), int) else 0
            coverage = (with_schema / total * 100) if total > 0 else 0

            self._add_examples_header(f"Copertura dati strutturati: {with_schema}/{total} pagine ({coverage:.1f}%)")

            types = data.get('schema_types', {})
            if types and isinstance(types, dict):
                self._add_examples_header("Tipi Schema.org rilevati:")
                rows = [[str(schema_type), str(count)] for schema_type, count in types.items()]
                self._add_examples_table(["Tipo Schema", "N. Pagine"], rows)

            issues = data.get('issues', {})
            if not isinstance(issues, dict):
                issues = {}
            errors = issues.get('errors', 0) if isinstance(issues.get('errors', 0), int) else 0
            if errors > 0:
                self._add_examples_header(f"⚠️ {errors} errori di validazione rilevati")

                error_list = issues.get('error_list', [])
                if error_list and isinstance(error_list, list):
                    rows = [[str(item.get('url', 'N/A'))[:40], str(item.get('error', 'N/A'))[:40]]
                            for item in error_list[:5] if isinstance(item, dict)]
                    if rows:
                        self._add_examples_table(["Pagina", "Errore"], rows)

        elif section_key == 'url':
            url_issues = data.get('url_issues', {})
            if not isinstance(url_issues, dict):
                url_issues = {}

            # URLs with underscore
            underscore_list = url_issues.get('underscore_list', [])
            if underscore_list and isinstance(underscore_list, list):
                self._add_examples_header("URL con underscore (usare dash invece):")
                self._add_url_list(underscore_list, max_items=10)

            # URLs with double slash
            double_slash_list = url_issues.get('double_slash_list', [])
            if double_slash_list and isinstance(double_slash_list, list):
                self._add_examples_header("URL con doppio slash:")
                self._add_url_list(double_slash_list, max_items=10)

            # Too long URLs
            long_urls = url_issues.get('long_urls_list', [])
            if long_urls and isinstance(long_urls, list):
                self._add_examples_header("URL troppo lunghi (>115 caratteri):")
                rows = [[str(url)[:60] + "...", str(len(str(url)))] for url in long_urls[:5]]
                if rows:
                    self._add_examples_table(["URL", "Lunghezza"], rows)

        elif section_key == 'sitemap':
            sitemap = data.get('sitemap', {})
            if not isinstance(sitemap, dict):
                sitemap = {}

            urls_count = sitemap.get('urls_count', 0)
            if isinstance(urls_count, int) and urls_count > 0:
                self._add_examples_header(f"Sitemap contiene {urls_count} URL")

            # URLs not in sitemap
            not_in_sitemap = sitemap.get('not_in_sitemap_list', [])
            if not_in_sitemap and isinstance(not_in_sitemap, list):
                self._add_examples_header("Pagine indicizzabili non presenti in sitemap:")
                self._add_url_list(not_in_sitemap, max_items=10)

            # URLs in sitemap but not crawlable
            not_crawlable = sitemap.get('not_crawlable_list', [])
            if not_crawlable and isinstance(not_crawlable, list):
                self._add_examples_header("URL in sitemap ma non scansionabili:")
                self._add_url_list(not_crawlable, max_items=10)

        elif section_key == 'errors':
            redirects = data.get('redirects', {})
            if not isinstance(redirects, dict):
                redirects = {}

            # Links to 404
            links_to_404 = redirects.get('internal_to_404_list', [])
            if links_to_404 and isinstance(links_to_404, list):
                self._add_examples_header("Link interni che puntano a pagine 404:")
                rows = []
                for item in links_to_404[:10]:
                    if isinstance(item, dict):
                        rows.append([item.get('source', 'N/A')[:40], item.get('target', 'N/A')[:40]])
                    else:
                        rows.append([str(item)[:40], ""])
                if rows:
                    self._add_examples_table(["Pagina origine", "Link rotto"], rows)

            # Redirect chains
            chains = redirects.get('redirect_chains_list', [])
            if chains and isinstance(chains, list):
                self._add_examples_header("Catene di redirect rilevate:")
                rows = []
                for item in chains[:5]:
                    if isinstance(item, dict):
                        rows.append([item.get('start', 'N/A')[:40], str(item.get('hops', 0))])
                    else:
                        rows.append([str(item)[:40], ""])
                if rows:
                    self._add_examples_table(["URL iniziale", "N. hop"], rows)

    def _add_image(self, image_path: Path, caption: str = None, width: float = 5.0):
        """Add image to document."""
        if image_path.exists():
            self.doc.add_picture(str(image_path), width=Inches(width))
            if caption:
                p = self.doc.add_paragraph(caption)
                p.italic = True
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def _add_priority_table(self, items: List[tuple]):
        """Add priority table."""
        self.doc.add_heading('5. PRIORITÀ E IMPORTANZA', 1)

        table = self.doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Header
        header_cells = table.rows[0].cells
        header_cells[0].text = 'Elemento'
        header_cells[1].text = 'Criticità'
        header_cells[2].text = 'Priorità'

        for cell in header_cells:
            cell.paragraphs[0].runs[0].bold = True

        # Data rows
        for name, criticality, priority in items:
            row_cells = table.add_row().cells
            row_cells[0].text = name
            row_cells[1].text = str(criticality)
            row_cells[2].text = str(priority)

        self.doc.add_paragraph()
        p = self.doc.add_paragraph('Criticità: 1=Alta, 2=Media, 3=Bassa')
        p.italic = True
        p = self.doc.add_paragraph('Priorità: 1=Alta, 2=Media, 3=Bassa')
        p.italic = True

    def generate(
        self,
        architecture_data: Dict[str, Any],
        content_data: Dict[str, Any],
        technical_data: Dict[str, Any],
        duplicates_data: Dict[str, Any],
        structured_data: Dict[str, Any],
        screenshots_dir: Optional[Path] = None,
        strategic_linking_data: Optional[Dict[str, Any]] = None
    ) -> Document:
        """Generate complete DOCX report.

        Args:
            architecture_data: Architecture analysis summary
            content_data: Content analysis summary
            technical_data: Technical analysis summary
            duplicates_data: Duplicates analysis summary
            structured_data: Structured data analysis summary
            screenshots_dir: Directory containing screenshots
            strategic_linking_data: Strategic linking analysis summary

        Returns:
            Document object
        """
        # Store strategic linking data for use in section generation
        self._strategic_linking_data = strategic_linking_data or {}
        self._setup_document()
        self._add_title_page()
        self._add_toc()

        # Introduction
        self.doc.add_heading('1. INTRODUZIONE', 1)
        self.doc.add_heading('1.1 Gli obiettivi', 2)
        self.doc.add_paragraph(self.narrative.generate_introduction())

        self.doc.add_heading('1.2 La struttura', 2)
        self.doc.add_paragraph(self.narrative.generate_structure_intro())

        # Architecture
        self.doc.add_heading('2. ARCHITETTURA SITO WEB', 1)

        # 2.1 Alberatura
        alberatura = self._generate_section_with_ai('alberatura', architecture_data)
        if alberatura is None:
            alberatura = self.narrative.generate_alberatura(architecture_data)
        self._add_section_with_examples('2.1', alberatura, architecture_data, 'alberatura')

        # 2.2 Canonical
        canonical_data = {**architecture_data, 'duplicates_data': duplicates_data}
        canonical = self._generate_section_with_ai('canonical', canonical_data)
        if canonical is None:
            canonical = self.narrative.generate_canonical(architecture_data, duplicates_data)
        self._add_section_with_examples('2.2', canonical, canonical_data, 'canonical')

        # 2.3 Hreflang
        hreflang = self._generate_section_with_ai('hreflang', architecture_data)
        if hreflang is None:
            hreflang = self.narrative.generate_hreflang(architecture_data)
        self._add_section_with_examples('2.3', hreflang, architecture_data, 'hreflang')

        # 2.4 URL
        url_issues = architecture_data.get('url_issues', {})
        self._add_section(
            '2.4', 'Struttura URL',
            self.narrative.get_premise('url'),
            self._get_url_situation(url_issues),
            self._get_url_improvements(url_issues)
        )
        self._add_section_examples('url', architecture_data)

        # 2.5 Menu
        self._add_section(
            '2.5', 'Menu di navigazione',
            self.narrative.get_premise('menu'),
            'Il menu di navigazione è stato analizzato per verificare la copertura delle sezioni principali.',
            'Si consiglia di verificare che tutte le sezioni importanti siano raggiungibili dal menu principale.'
        )

        # 2.6 Title
        title_section = self._generate_section_with_ai('title', content_data)
        if title_section is None:
            title_section = self.narrative.generate_title(content_data)
        self._add_section_with_examples('2.6', title_section, content_data, 'title')

        # 2.7 Description
        desc_section = self._generate_section_with_ai('description', content_data)
        if desc_section is None:
            desc_section = self.narrative.generate_description(content_data)
        self._add_section_with_examples('2.7', desc_section, content_data, 'description')

        # 2.8 Keywords
        self._add_section(
            '2.8', 'Meta Keywords',
            self.narrative.get_premise('keywords'),
            f'{content_data.get("pages_with_keywords", 0)} pagine presentano meta keywords.',
            'Non sono necessari miglioramenti in quanto i motori di ricerca non utilizzano più questo tag.'
        )

        # 2.9 Performance
        perf_section = self._generate_section_with_ai('performance', technical_data)
        if perf_section is None:
            perf_section = self.narrative.generate_performance(technical_data)
        self._add_section_with_examples('2.9', perf_section, technical_data, 'performance')

        # 2.10-2.13 Technical sections
        self._add_technical_sections(technical_data)

        # Content sections
        self.doc.add_heading('3. CONTENUTI DEL SITO WEB', 1)

        # 3.1 Headings
        headings_section = self._generate_section_with_ai('headings', content_data)
        if headings_section is None:
            headings_section = self.narrative.generate_headings(content_data)
        self._add_section_with_examples('3.1', headings_section, content_data, 'headings')

        # 3.2 Paragraphs
        thin_pages = content_data.get('content', {}).get('thin_pages', 0)
        self._add_section(
            '3.2', 'Paragrafi',
            self.narrative.get_premise('paragraphs'),
            f'Sono state rilevate {thin_pages} pagine con contenuto scarso.' if thin_pages > 0 else 'I contenuti testuali sono generalmente adeguati.',
            'Si consiglia di arricchire le pagine con contenuto scarso.' if thin_pages > 0 else 'Non sono necessari miglioramenti.'
        )

        # 3.3 Images
        images_section = self._generate_section_with_ai('images', content_data)
        if images_section is None:
            images_section = self.narrative.generate_images(content_data)
        self._add_section_with_examples('3.3', images_section, content_data, 'images')

        # 3.4 Linking (Strategic Analysis)
        # Combine technical data with strategic linking data
        linking_data = {**technical_data}
        if self._strategic_linking_data:
            linking_data['strategic_linking'] = self._strategic_linking_data

        linking_section = self._generate_section_with_ai('linking', linking_data)
        if linking_section is None:
            linking_section = self.narrative.generate_linking(linking_data)
        self._add_section_with_examples('3.4', linking_section, linking_data, 'linking')

        # Structured data
        self.doc.add_heading('4. MICRODATI', 1)
        struct_section = self._generate_section_with_ai('structured_data', structured_data)
        if struct_section is None:
            struct_section = self.narrative.generate_structured_data(structured_data)
        self._add_section_with_examples('4.1', struct_section, structured_data, 'structured_data')

        # Priority table
        self._add_priority_table(self._get_priority_items(
            architecture_data, content_data, technical_data, duplicates_data, structured_data
        ))

        return self.doc

    def _get_url_situation(self, url_issues: Dict) -> str:
        """Get URL situation text."""
        underscore = url_issues.get('underscore', 0)
        double_slash = url_issues.get('double_slash', 0)

        if underscore > 0 or double_slash > 0:
            issues = []
            if underscore > 0:
                issues.append(f'{underscore} URL con underscore')
            if double_slash > 0:
                issues.append(f'{double_slash} URL con doppi slash')
            return f'Sono stati rilevati alcuni problemi: {", ".join(issues)}.'
        return 'Le URL del sito sono generalmente ben strutturate.'

    def _get_url_improvements(self, url_issues: Dict) -> str:
        """Get URL improvements text."""
        underscore = url_issues.get('underscore', 0)
        double_slash = url_issues.get('double_slash', 0)

        if underscore > 0 or double_slash > 0:
            return 'Si consiglia di correggere le URL problematiche usando dash (-) invece di underscore e rimuovendo i doppi slash.'
        return 'Non sono necessari miglioramenti.'

    def _add_technical_sections(self, data: Dict):
        """Add technical sections."""
        # Sitemap
        sitemap = data.get('sitemap', {})
        self._add_section(
            '2.10', 'Mappa del sito (sitemap.xml)',
            self.narrative.get_premise('sitemap'),
            f"{'La sitemap è presente' if sitemap.get('found') else 'La sitemap non è stata trovata'}. Contiene {sitemap.get('urls_count', 0)} URL.",
            'Si consiglia di mantenere la sitemap aggiornata con tutte le pagine indicizzabili.'
        )
        self._add_section_examples('sitemap', data)

        # Robots.txt
        robots = data.get('robots_txt', {})
        self._add_section(
            '2.11', 'Robots.txt',
            self.narrative.get_premise('robots'),
            f"{'Il file robots.txt è presente' if robots.get('found') else 'Il file robots.txt non è stato trovato'}.",
            'Verificare che non siano bloccate risorse necessarie per il rendering delle pagine.'
        )

        # HTTPS
        https = data.get('https', {})
        self._add_section(
            '2.12', 'HTTP e HTTPS',
            self.narrative.get_premise('https'),
            f"Il sito {'utilizza' if https.get('uses_https') else 'non utilizza'} il protocollo HTTPS.",
            'Verificare che tutti i link interni utilizzino HTTPS.' if https.get('uses_https') else 'Si consiglia di migrare a HTTPS.'
        )

        # 404 and redirects
        redirects = data.get('redirects', {})
        errors_404 = redirects.get('internal_to_404', 0)
        self._add_section(
            '2.13', 'Errori 404 e redirect 301',
            self.narrative.get_premise('errors'),
            f'Sono stati rilevati {errors_404} link interni che puntano a pagine 404.' if errors_404 > 0 else 'Non sono stati rilevati link rotti significativi.',
            'Correggere i link rotti e implementare redirect dove necessario.' if errors_404 > 0 else 'Non sono necessari miglioramenti.'
        )
        self._add_section_examples('errors', data)

    def _get_priority_items(self, arch, content, tech, dup, struct) -> List[tuple]:
        """Get priority table items."""
        items = [
            ('Alberatura', self._calc_severity(arch, 'deep_pages_count', 5, 15), '2'),
            ('Canonicalizzazione', self._calc_severity(arch.get('canonical_issues', {}), 'missing', 10, 30), '1'),
            ('Hreflang', self._calc_severity(arch.get('hreflang', {}), 'non_reciprocal', 5, 15), '2'),
            ('Struttura URL', self._calc_severity(arch.get('url_issues', {}), 'double_slash', 5, 15), '2'),
            ('Title', self._calc_severity(content.get('titles', {}), 'without_title', 5, 15), '1'),
            ('Meta Description', self._calc_severity(content.get('descriptions', {}), 'without_description', 10, 30), '1'),
            ('Intestazioni', self._calc_severity(content.get('headings', {}), 'without_h1', 5, 15), '1'),
            ('Immagini', '2', '2'),
            ('Linking interno', '2', '1'),
            ('Dati Strutturati', '2' if struct.get('pages_with_schema', 0) > 0 else '1', '2'),
        ]
        return items

    def _calc_severity(self, data: Dict, key: str, threshold_medium: int, threshold_high: int) -> str:
        """Calculate severity."""
        value = data.get(key, 0)
        if value >= threshold_high:
            return '1'
        elif value >= threshold_medium:
            return '2'
        return '3'

    def save(self, filename: str = None) -> Path:
        """Save document to file.

        Args:
            filename: Output filename (optional)

        Returns:
            Path to saved file
        """
        if self.doc is None:
            raise ValueError("Document not generated yet")

        if filename is None:
            domain = self.site_url.replace("https://", "").replace("http://", "").replace("/", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Audit SEO - {self.site_name} - {timestamp}.docx"

        output_path = self.output_dir / filename
        self.doc.save(str(output_path))
        return output_path
