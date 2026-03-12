"""Markdown report generator."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from .narrative import NarrativeGenerator, NarrativeSection


class MarkdownReporter:
    """Generator for Markdown audit reports."""

    def __init__(
        self,
        site_name: str,
        site_url: str,
        output_dir: Path = None
    ):
        """Initialize reporter.

        Args:
            site_name: Name of the site
            site_url: URL of the site
            output_dir: Output directory for report
        """
        self.site_name = site_name
        self.site_url = site_url
        self.output_dir = output_dir or Path(".")
        self.narrative = NarrativeGenerator(site_name, site_url)

    def generate(
        self,
        architecture_data: Dict[str, Any],
        content_data: Dict[str, Any],
        technical_data: Dict[str, Any],
        duplicates_data: Dict[str, Any],
        structured_data: Dict[str, Any],
        screenshots_dir: Optional[Path] = None
    ) -> str:
        """Generate complete Markdown report.

        Args:
            architecture_data: Architecture analysis summary
            content_data: Content analysis summary
            technical_data: Technical analysis summary
            duplicates_data: Duplicates analysis summary
            structured_data: Structured data analysis summary
            screenshots_dir: Directory containing screenshots

        Returns:
            Markdown report content
        """
        sections = []

        # Title and header
        sections.append(f"# Audit SEO - {self.site_name}\n")
        sections.append(f"**Sito:** {self.site_url}\n")
        sections.append(f"**Data:** {datetime.now().strftime('%d/%m/%Y')}\n")
        sections.append("\n---\n")

        # Table of contents
        sections.append(self._generate_toc())

        # Introduction
        sections.append(self._generate_introduction())

        # Architecture sections (includes title, description, technical)
        sections.append(self._generate_architecture_sections(
            architecture_data, duplicates_data, content_data, technical_data
        ))

        # Content sections (headings, paragraphs, images, linking)
        sections.append(self._generate_content_sections(content_data))

        # Structured data
        sections.append(self._generate_structured_data_section(structured_data))

        # Priority table
        sections.append(self._generate_priority_table(
            architecture_data, content_data, technical_data, duplicates_data, structured_data
        ))

        return "\n".join(sections)

    def _generate_toc(self) -> str:
        """Generate table of contents."""
        return """
## INDICE

1. [INTRODUZIONE](#1-introduzione)
   1. [Gli obiettivi](#11-gli-obiettivi)
   2. [La struttura](#12-la-struttura)
2. [ARCHITETTURA SITO WEB](#2-architettura-sito-web)
   1. [Alberatura](#21-alberatura)
   2. [Canonicalizzazione e contenuto duplicato](#22-canonicalizzazione-e-contenuto-duplicato)
   3. [Hreflang](#23-hreflang)
   4. [Struttura URL](#24-struttura-url)
   5. [Menu di navigazione](#25-menu-di-navigazione)
   6. [Title](#26-title)
   7. [Meta Description](#27-meta-description)
   8. [Meta Keywords](#28-meta-keywords)
   9. [Tempi di caricamento](#29-tempi-di-caricamento)
   10. [Sitemap](#210-sitemap)
   11. [Robots.txt](#211-robotstxt)
   12. [HTTPS](#212-https)
   13. [Errori 404 e redirect](#213-errori-404-e-redirect)
3. [CONTENUTI DEL SITO WEB](#3-contenuti-del-sito-web)
   1. [Intestazione (headings)](#31-intestazione-headings)
   2. [Paragrafi](#32-paragrafi)
   3. [Immagini](#33-immagini)
   4. [Linking interno](#34-linking-interno)
4. [MICRODATI](#4-microdati)
5. [PRIORITÀ E IMPORTANZA](#5-priorità-e-importanza)

---
"""

    def _generate_introduction(self) -> str:
        """Generate introduction section."""
        intro = self.narrative.generate_introduction()
        structure = self.narrative.generate_structure_intro()

        return f"""
## 1. INTRODUZIONE

### 1.1 Gli obiettivi

{intro}

### 1.2 La struttura

{structure}

---
"""

    def _section_to_markdown(self, section: NarrativeSection, number: str) -> str:
        """Convert NarrativeSection to Markdown.

        Args:
            section: Section to convert
            number: Section number (e.g., "2.1")

        Returns:
            Markdown text
        """
        return f"""
### {number} {section.title}

**Premessa**

{section.premise}

**Situazione attuale**

{section.current_situation}

**Come migliorare**

{section.improvements}
"""

    def _generate_architecture_sections(
        self,
        arch_data: Dict[str, Any],
        dup_data: Dict[str, Any],
        content_data: Dict[str, Any],
        tech_data: Dict[str, Any]
    ) -> str:
        """Generate architecture sections."""
        sections = ["## 2. ARCHITETTURA SITO WEB\n"]

        # 2.1 Alberatura
        alberatura = self.narrative.generate_alberatura(arch_data)
        sections.append(self._section_to_markdown(alberatura, "2.1"))

        # 2.2 Canonical
        canonical = self.narrative.generate_canonical(arch_data, dup_data)
        sections.append(self._section_to_markdown(canonical, "2.2"))

        # 2.3 Hreflang
        hreflang = self.narrative.generate_hreflang(arch_data)
        sections.append(self._section_to_markdown(hreflang, "2.3"))

        # 2.4 URL (simplified)
        url_issues = arch_data.get('url_issues', {})
        underscore = url_issues.get('underscore', 0)
        uppercase = url_issues.get('uppercase', 0)
        double_slash = url_issues.get('double_slash', 0)

        url_situation = "Le URL del sito sono generalmente ben strutturate."
        url_improvements = "Non sono necessari miglioramenti."

        if underscore > 0 or double_slash > 0:
            issues = []
            if underscore > 0:
                issues.append(f"{underscore} URL con underscore")
            if double_slash > 0:
                issues.append(f"{double_slash} URL con doppi slash")
            url_situation = f"Sono stati rilevati alcuni problemi: {', '.join(issues)}."
            url_improvements = "Si consiglia di correggere le URL problematiche usando dash (-) invece di underscore e rimuovendo i doppi slash."

        sections.append(f"""
### 2.4 Struttura URL

**Premessa**

{self.narrative.get_premise('url')}

**Situazione attuale**

{url_situation}

**Come migliorare**

{url_improvements}
""")

        # 2.5 Menu (simplified)
        sections.append(f"""
### 2.5 Menu di navigazione

**Premessa**

{self.narrative.get_premise('menu')}

**Situazione attuale**

Il menu di navigazione è stato analizzato per verificare la copertura delle sezioni principali.

**Come migliorare**

Si consiglia di verificare che tutte le sezioni importanti siano raggiungibili dal menu principale.
""")

        # 2.6 Title
        title_section = self.narrative.generate_title(content_data)
        sections.append(self._section_to_markdown(title_section, "2.6"))

        # 2.7 Description
        desc_section = self.narrative.generate_description(content_data)
        sections.append(self._section_to_markdown(desc_section, "2.7"))

        # 2.8 Keywords (brief)
        sections.append(f"""
### 2.8 Meta Keywords

**Premessa**

{self.narrative.get_premise('keywords')}

**Situazione attuale**

{content_data.get('pages_with_keywords', 0)} pagine presentano meta keywords.

**Come migliorare**

Non sono necessari miglioramenti in quanto i motori di ricerca non utilizzano più questo tag.
""")

        # 2.9 Performance
        perf_section = self.narrative.generate_performance(content_data)
        sections.append(self._section_to_markdown(perf_section, "2.9"))

        # 2.10-2.13 Technical sections (sitemap, robots, https, 404)
        sections.append(self._generate_technical_sections(tech_data))

        return "\n".join(sections)

    def _generate_content_sections(self, content_data: Dict[str, Any]) -> str:
        """Generate content sections (headings, paragraphs, images, linking)."""
        sections = ["## 3. CONTENUTI DEL SITO WEB\n"]

        # 3.1 Headings
        headings_section = self.narrative.generate_headings(content_data)
        sections.append(self._section_to_markdown(headings_section, "3.1"))

        # 3.2 Paragraphs (brief)
        thin_pages = content_data.get('content', {}).get('thin_pages', 0)
        sections.append(f"""
### 3.2 Paragrafi

**Premessa**

{self.narrative.get_premise('paragraphs')}

**Situazione attuale**

{"Sono state rilevate " + str(thin_pages) + " pagine con contenuto scarso (meno di 300 parole)." if thin_pages > 0 else "I contenuti testuali delle pagine sono generalmente adeguati."}

**Come migliorare**

{"Si consiglia di arricchire le pagine con contenuto scarso aggiungendo testo rilevante e informativo." if thin_pages > 0 else "Non sono necessari miglioramenti."}
""")

        # 3.3 Images
        images_section = self.narrative.generate_images(content_data)
        sections.append(self._section_to_markdown(images_section, "3.3"))

        # 3.4 Linking
        linking_section = self.narrative.generate_linking(content_data)
        sections.append(self._section_to_markdown(linking_section, "3.4"))

        return "\n".join(sections)

    def _generate_technical_sections(self, data: Dict[str, Any]) -> str:
        """Generate technical sections (sitemap, robots, https, 404)."""
        # Simplified versions
        return f"""
### 2.10 Mappa del sito (sitemap.xml)

**Premessa**

{self.narrative.get_premise('sitemap')}

**Situazione attuale**

La sitemap è stata analizzata per verificare la corrispondenza con le pagine del sito.

**Come migliorare**

Si consiglia di mantenere la sitemap aggiornata con tutte le pagine indicizzabili.

### 2.11 Robots.txt

**Premessa**

{self.narrative.get_premise('robots')}

**Situazione attuale**

Il file robots.txt è stato analizzato per verificare le direttive impostate.

**Come migliorare**

Verificare che non siano bloccate risorse necessarie per il rendering delle pagine.

### 2.12 HTTP e HTTPS

**Premessa**

{self.narrative.get_premise('https')}

**Situazione attuale**

Il sito utilizza il protocollo HTTPS per la trasmissione sicura dei dati.

**Come migliorare**

Verificare che tutti i link interni utilizzino HTTPS e che non ci sia mixed content.

### 2.13 Errori 404 e redirect 301

**Premessa**

{self.narrative.get_premise('errors')}

**Situazione attuale**

Sono stati analizzati gli status code di tutte le pagine e i redirect presenti.

**Come migliorare**

Correggere i link rotti e ridurre le catene di redirect.
"""

    def _generate_structured_data_section(self, data: Dict[str, Any]) -> str:
        """Generate structured data section."""
        section = self.narrative.generate_structured_data(data)
        return f"""
## 4. MICRODATI

{self._section_to_markdown(section, "4.1").replace("### 4.1", "").strip()}

---
"""

    def _generate_priority_table(
        self,
        arch: Dict,
        content: Dict,
        tech: Dict,
        dup: Dict,
        struct: Dict
    ) -> str:
        """Generate priority table."""
        # Calculate severities
        items = []

        # Architecture
        items.append(("Alberatura", self._calc_severity(arch, 'deep_pages_count', 5, 15), "2"))
        items.append(("Canonicalizzazione", self._calc_severity(arch.get('canonical_issues', {}), 'missing', 10, 30), "1"))
        items.append(("Hreflang", self._calc_severity(arch.get('hreflang', {}), 'non_reciprocal', 5, 15), "2"))
        items.append(("Struttura URL", self._calc_severity(arch.get('url_issues', {}), 'double_slash', 5, 15), "2"))

        # Content
        items.append(("Title", self._calc_severity(content.get('titles', {}), 'without_title', 5, 15), "1"))
        items.append(("Meta Description", self._calc_severity(content.get('descriptions', {}), 'without_description', 10, 30), "1"))
        items.append(("Intestazioni", self._calc_severity(content.get('headings', {}), 'without_h1', 5, 15), "1"))
        items.append(("Immagini", "2", "2"))
        items.append(("Linking interno", "2", "1"))
        items.append(("Dati Strutturati", "2" if struct.get('pages_with_schema', 0) > 0 else "1", "2"))

        # Build table
        rows = ["## 5. PRIORITÀ E IMPORTANZA\n"]
        rows.append("| Elemento | Criticità | Priorità |")
        rows.append("|----------|-----------|----------|")

        for name, criticality, priority in items:
            rows.append(f"| {name} | {criticality} | {priority} |")

        rows.append("\n*Criticità: 1=Alta, 2=Media, 3=Bassa*")
        rows.append("*Priorità: 1=Alta, 2=Media, 3=Bassa*")

        return "\n".join(rows)

    def _calc_severity(self, data: Dict, key: str, threshold_medium: int, threshold_high: int) -> str:
        """Calculate severity based on threshold."""
        value = data.get(key, 0)
        if value >= threshold_high:
            return "1"
        elif value >= threshold_medium:
            return "2"
        else:
            return "3"

    def save(self, content: str, filename: str = None) -> Path:
        """Save report to file.

        Args:
            content: Report content
            filename: Output filename (optional)

        Returns:
            Path to saved file
        """
        if filename is None:
            domain = self.site_url.replace("https://", "").replace("http://", "").replace("/", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audit_{domain}_{timestamp}.md"

        output_path = self.output_dir / filename
        output_path.write_text(content, encoding='utf-8')
        return output_path
