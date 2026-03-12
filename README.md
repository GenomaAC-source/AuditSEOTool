# AuditSEO Tool

Professional SEO audit tool that analyzes websites and generates comprehensive reports in Markdown and DOCX formats.

## Features

- **Async Crawler**: Fast, concurrent crawling with configurable rate limiting
- **Scalable**: Handles sites with thousands of pages using SQLite storage
- **Content Duplicate Detection**: Intelligent similarity analysis using SimHash
- **Comprehensive Analysis**:
  - Site architecture and URL structure
  - Canonical tags and hreflang
  - Title, meta description, headings
  - Images and alt text
  - Internal linking
  - Structured data (Schema.org)
  - Performance metrics
  - Robots.txt and sitemap
- **Professional Reports**: Consultant-style narrative reports
- **Screenshot Capture**: Visual documentation (requires Playwright)

## Installation

```bash
# Clone or download the repository
cd AuditSEOTool

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (optional, for screenshots)
playwright install chromium
```

## Usage

### Web Interface (Recommended)

```bash
streamlit run app.py
```

L'interfaccia web si aprirà automaticamente sulla porta **3030** (configurata in `.streamlit/config.toml`).
Se vuoi usare una porta diversa:

```bash
streamlit run app.py --server.port=8501
```

L'interfaccia permette di:
- Inserire l'URL del sito
- Configurare le opzioni
- Avviare l'audit
- Scaricare i report (MD, DOCX, JSON)

### Command Line

```bash
python audit.py https://www.example.com
```

### With Options

```bash
# Limit pages (for testing)
python audit.py https://www.example.com --max-pages 100

# Generate only Markdown
python audit.py https://www.example.com --format md

# Disable screenshots
python audit.py https://www.example.com --no-screenshots

# Resume interrupted crawl
python audit.py https://www.example.com --resume

# Generate report from existing data
python audit.py https://www.example.com --report-only

# Custom concurrency
python audit.py https://www.example.com --concurrency 20 --delay 50
```

### All Options

```
Options:
  -m, --max-pages INTEGER    Maximum pages to crawl (default: unlimited)
  -o, --output TEXT          Output filename (without extension)
  -f, --format [md|docx|both] Output format (default: both)
  --screenshots / --no-screenshots
                             Capture screenshots (default: enabled)
  --resume                   Resume previous crawl
  --report-only              Generate report from existing data
  -c, --concurrency INTEGER  Concurrent requests (default: 10)
  -d, --delay INTEGER        Delay between requests in ms (default: 100)
  -s, --similarity FLOAT     Similarity threshold for duplicates (default: 0.85)
  -v, --verbose              Verbose output
  --help                     Show this message and exit
```

## Output

The tool generates:

1. **Markdown Report** (`audit_domain_timestamp.md`)
2. **DOCX Report** (`Audit SEO - SiteName - timestamp.docx`)
3. **JSON Data** (`audit_domain_timestamp_data.json`)
4. **Screenshots** (in `data/domain/screenshots/`)

## Report Structure

1. **Introduction**: Audit objectives and document structure
2. **Site Architecture**:
   - Site structure (alberatura)
   - Canonicalization and duplicates
   - Hreflang implementation
   - URL structure
   - Navigation menus
   - Title tags
   - Meta descriptions
   - Performance
   - Sitemap and robots.txt
   - HTTPS
   - 404 errors and redirects
3. **Content**:
   - Headings (H1-H6)
   - Text content
   - Images
   - Internal linking
4. **Structured Data**: Schema.org implementation
5. **Priority Table**: Issues ranked by severity and priority

## Running Tests

```bash
pytest tests/ -v
```

## Requirements

- Python 3.11+
- See `requirements.txt` for dependencies

## License

MIT License
