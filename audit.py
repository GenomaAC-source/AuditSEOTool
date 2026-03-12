#!/usr/bin/env python3
"""
AuditSEO Tool - Professional SEO Audit Tool

A comprehensive tool for analyzing websites and generating professional
SEO audit reports in Markdown and DOCX formats.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.database import CrawlDatabase
from src.crawler import AsyncCrawler, run_crawl
from src.analyzers import (
    ArchitectureAnalyzer,
    ContentAnalyzer,
    TechnicalAnalyzer,
    DuplicateAnalyzer,
    StructuredDataAnalyzer
)
from src.reporters import MarkdownReporter, DocxReporter
from src.screenshot import capture_audit_screenshots, is_playwright_available

console = Console()


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc or url


def get_site_name(url: str) -> str:
    """Get site name from URL."""
    domain = extract_domain(url)
    # Remove www. and TLD for cleaner name
    name = domain.replace('www.', '').split('.')[0]
    return name.title()


@click.command()
@click.argument('url')
@click.option('--max-pages', '-m', type=int, default=None,
              help='Maximum pages to crawl (default: unlimited)')
@click.option('--output', '-o', type=str, default=None,
              help='Output filename (without extension)')
@click.option('--format', '-f', type=click.Choice(['md', 'docx', 'both']), default='both',
              help='Output format (default: both)')
@click.option('--screenshots/--no-screenshots', default=True,
              help='Capture screenshots (requires playwright)')
@click.option('--resume', is_flag=True, default=False,
              help='Resume previous crawl')
@click.option('--report-only', is_flag=True, default=False,
              help='Generate report from existing data (no crawl)')
@click.option('--concurrency', '-c', type=int, default=10,
              help='Number of concurrent requests (default: 10)')
@click.option('--delay', '-d', type=int, default=100,
              help='Delay between requests in ms (default: 100)')
@click.option('--similarity', '-s', type=float, default=0.85,
              help='Similarity threshold for duplicates (default: 0.85)')
@click.option('--verbose', '-v', is_flag=True, default=False,
              help='Verbose output')
def main(
    url: str,
    max_pages: Optional[int],
    output: Optional[str],
    format: str,
    screenshots: bool,
    resume: bool,
    report_only: bool,
    concurrency: int,
    delay: int,
    similarity: float,
    verbose: bool
):
    """
    AuditSEO Tool - Analyze a website and generate SEO audit report.

    URL: The website URL to analyze (e.g., https://www.example.com)
    """
    # Normalize URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    domain = extract_domain(url)
    site_name = get_site_name(url)

    # Setup paths
    data_dir = Path('data')
    domain_dir = data_dir / domain.replace('.', '_').replace(':', '_')
    screenshots_dir = domain_dir / 'screenshots'

    # Initialize database
    db = CrawlDatabase(domain, data_dir)

    console.print(Panel.fit(
        f"[bold blue]AuditSEO Tool[/bold blue]\n"
        f"Sito: {url}\n"
        f"Domain: {domain}",
        title="SEO Audit"
    ))

    # Crawl phase
    if not report_only:
        console.print("\n[bold]Fase 1: Crawling del sito[/bold]")

        with console.status("[cyan]Inizializzazione crawler..."):
            crawler = AsyncCrawler(
                start_url=url,
                db=db,
                max_pages=max_pages,
                concurrency=concurrency,
                delay_ms=delay
            )

        # Run crawl
        stats = asyncio.run(crawler.crawl(resume=resume))

        # Show crawl stats
        table = Table(title="Statistiche Crawl")
        table.add_column("Metrica", style="cyan")
        table.add_column("Valore", style="green")

        table.add_row("URL totali crawlati", str(stats.get('total_urls_crawled', 0)))
        table.add_row("Pagine analizzate (200 OK)", str(stats.get('total_pages', 0)))
        table.add_row("Redirect (301, 302, etc.)", str(stats.get('total_redirects', 0)))
        table.add_row("Errori (4xx, 5xx)", str(stats.get('total_errors', 0)))

        # Show detailed status codes
        table.add_row("", "")  # Empty row as separator
        for status, count in sorted(stats.get('status_codes', {}).items()):
            table.add_row(f"  Status {status}", str(count))

        console.print(table)

    # Check if we have data
    if db.get_pages_count() == 0:
        console.print("[red]Errore: Nessuna pagina nel database. Esegui prima il crawl.[/red]")
        sys.exit(1)

    # Analysis phase
    console.print("\n[bold]Fase 2: Analisi SEO[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # Architecture analysis
        task = progress.add_task("[cyan]Analisi architettura...", total=None)
        arch_analyzer = ArchitectureAnalyzer(db)
        arch_report = arch_analyzer.analyze()
        arch_summary = arch_analyzer.get_summary()
        progress.update(task, completed=True)

        # Content analysis
        task = progress.add_task("[cyan]Analisi contenuti...", total=None)
        content_analyzer = ContentAnalyzer(db)
        content_report = content_analyzer.analyze()
        content_summary = content_analyzer.get_summary()
        progress.update(task, completed=True)

        # Technical analysis
        task = progress.add_task("[cyan]Analisi tecnica...", total=None)
        tech_analyzer = TechnicalAnalyzer(db, url)
        tech_report = tech_analyzer.analyze()
        tech_summary = tech_analyzer.get_summary()
        progress.update(task, completed=True)

        # Duplicate analysis
        task = progress.add_task("[cyan]Analisi duplicati...", total=None)
        dup_analyzer = DuplicateAnalyzer(db, similarity)
        dup_report = dup_analyzer.analyze()
        dup_summary = dup_analyzer.get_summary()
        progress.update(task, completed=True)

        # Structured data analysis
        task = progress.add_task("[cyan]Analisi dati strutturati...", total=None)
        struct_analyzer = StructuredDataAnalyzer(db)
        struct_report = struct_analyzer.analyze()
        struct_summary = struct_analyzer.get_summary()
        progress.update(task, completed=True)

    # Screenshots
    screenshot_paths = {}
    if screenshots and is_playwright_available():
        console.print("\n[bold]Fase 3: Cattura screenshot[/bold]")
        try:
            screenshot_paths = asyncio.run(capture_audit_screenshots(
                url,
                screenshots_dir,
                include_mobile=True
            ))
            console.print(f"[green]Catturati {len(screenshot_paths)} screenshot[/green]")
        except Exception as e:
            console.print(f"[yellow]Screenshot non disponibili: {e}[/yellow]")
    elif screenshots and not is_playwright_available():
        console.print("[yellow]Playwright non installato. Screenshot disabilitati.[/yellow]")

    # Report generation
    console.print("\n[bold]Fase 4: Generazione report[/bold]")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output:
        base_filename = output
    else:
        base_filename = f"audit_{domain.replace('.', '_')}_{timestamp}"

    output_files = []

    # Markdown report
    if format in ('md', 'both'):
        with console.status("[cyan]Generazione report Markdown..."):
            md_reporter = MarkdownReporter(site_name, url, domain_dir)
            md_content = md_reporter.generate(
                arch_summary,
                content_summary,
                tech_summary,
                dup_summary,
                struct_summary,
                screenshots_dir if screenshot_paths else None
            )
            md_path = md_reporter.save(md_content, f"{base_filename}.md")
            output_files.append(md_path)
            console.print(f"[green]Report Markdown: {md_path}[/green]")

    # DOCX report
    if format in ('docx', 'both'):
        with console.status("[cyan]Generazione report DOCX..."):
            docx_reporter = DocxReporter(site_name, url, domain_dir)
            docx_reporter.generate(
                arch_summary,
                content_summary,
                tech_summary,
                dup_summary,
                struct_summary,
                screenshots_dir if screenshot_paths else None
            )
            docx_path = docx_reporter.save(f"Audit SEO - {site_name} - {timestamp}.docx")
            output_files.append(docx_path)
            console.print(f"[green]Report DOCX: {docx_path}[/green]")

    # Save raw data as JSON
    json_path = domain_dir / f"{base_filename}_data.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'url': url,
            'domain': domain,
            'crawled_at': timestamp,
            'architecture': arch_summary,
            'content': content_summary,
            'technical': tech_summary,
            'duplicates': dup_summary,
            'structured_data': struct_summary
        }, f, indent=2, ensure_ascii=False)
    output_files.append(json_path)
    console.print(f"[green]Dati JSON: {json_path}[/green]")

    # Summary
    stats = db.get_statistics()
    console.print("\n" + "=" * 60)
    console.print(Panel.fit(
        f"[bold green]Audit completato![/bold green]\n\n"
        f"Pagine analizzate (200 OK): {stats.get('total_pages', 0)}\n"
        f"URL totali crawlati: {stats.get('total_urls_crawled', 0)}\n"
        f"Redirect: {stats.get('total_redirects', 0)}\n"
        f"Errori: {stats.get('total_errors', 0)}\n"
        f"File generati: {len(output_files)}",
        title="Riepilogo"
    ))

    # Show key findings
    _show_key_findings(arch_summary, content_summary, tech_summary, dup_summary)


def _show_key_findings(arch, content, tech, dup):
    """Show key findings summary."""
    findings = []

    # Architecture
    if arch.get('orphan_pages_count', 0) > 0:
        findings.append(f"[yellow]• {arch['orphan_pages_count']} pagine orfane[/yellow]")

    if arch.get('canonical_issues', {}).get('missing', 0) > 0:
        findings.append(f"[yellow]• {arch['canonical_issues']['missing']} pagine senza canonical[/yellow]")

    # Content
    if content.get('titles', {}).get('without_title', 0) > 0:
        findings.append(f"[red]• {content['titles']['without_title']} pagine senza title[/red]")

    if content.get('headings', {}).get('without_h1', 0) > 0:
        findings.append(f"[red]• {content['headings']['without_h1']} pagine senza H1[/red]")

    # Duplicates
    if dup.get('duplicates', {}).get('exact', 0) > 0:
        findings.append(f"[yellow]• {dup['duplicates']['exact']} pagine duplicate[/yellow]")

    # Technical
    if tech.get('redirects', {}).get('internal_to_404', 0) > 0:
        findings.append(f"[red]• {tech['redirects']['internal_to_404']} link a pagine 404[/red]")

    if findings:
        console.print("\n[bold]Problemi principali rilevati:[/bold]")
        for finding in findings[:10]:
            console.print(finding)
    else:
        console.print("\n[bold green]Nessun problema critico rilevato![/bold green]")


if __name__ == '__main__':
    main()
