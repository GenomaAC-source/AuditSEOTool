from playwright.sync_api import sync_playwright
import json, os

SCREENSHOT_DIR = "/Users/andreacamolese/Desktop/AuditSEOTool/ClaudeSEO/.claude/worktrees/unruffled-williams/screenshots"

PAGES = [
    ("homepage", "https://ambito.it/"),
    ("chi-siamo", "https://ambito.it/chi-siamo/"),
    ("suite-mosaico", "https://ambito.it/suite-mosaico-digitai/"),
    ("contatti", "https://ambito.it/contatti/"),
]

VIEWPORTS = [
    ("mobile", 375, 812),
    ("desktop", 1280, 800),
]

def analyze_page(page, name, vp_name):
    """Extract key rendering metrics from the page."""
    data = page.evaluate("""() => {
        const result = {};

        // Viewport meta
        const vpMeta = document.querySelector('meta[name="viewport"]');
        result.viewportMeta = vpMeta ? vpMeta.getAttribute('content') : null;

        // H1
        const h1 = document.querySelector('h1');
        result.h1 = h1 ? { text: h1.innerText.trim().substring(0, 200), visible: h1.offsetHeight > 0 } : null;

        // CTAs (links/buttons with CTA-like text or classes)
        const allLinks = [...document.querySelectorAll('a, button')];
        result.ctas = allLinks.filter(el => {
            const t = (el.innerText || '').toLowerCase();
            const cls = (el.className || '').toLowerCase();
            return t.includes('contatt') || t.includes('scopri') || t.includes('richiedi') ||
                   t.includes('prova') || t.includes('demo') || t.includes('inizia') ||
                   cls.includes('cta') || cls.includes('btn') || cls.includes('button');
        }).slice(0, 15).map(el => {
            const rect = el.getBoundingClientRect();
            return {
                tag: el.tagName,
                text: (el.innerText || '').trim().substring(0, 80),
                href: el.href || null,
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                top: Math.round(rect.top),
                left: Math.round(rect.left),
                aboveFold: rect.top < window.innerHeight,
                classes: (el.className || '').substring(0, 100)
            };
        });

        // Navigation
        const nav = document.querySelector('nav, .navbar, .menu, header');
        result.hasNav = !!nav;
        const hamburger = document.querySelector('[class*="hamburger"], [class*="toggle"], [class*="mobile-menu"], .menu-toggle, button[aria-label*="menu"], button[aria-label*="Menu"]');
        result.hasHamburger = !!hamburger;

        // Images above fold
        const imgs = [...document.querySelectorAll('img')].slice(0, 20);
        result.images = imgs.map(img => {
            const rect = img.getBoundingClientRect();
            return {
                src: (img.src || '').substring(0, 120),
                alt: (img.alt || '').substring(0, 80),
                hasSrcset: !!img.srcset,
                hasSizes: !!img.sizes,
                naturalWidth: img.naturalWidth,
                naturalHeight: img.naturalHeight,
                displayWidth: Math.round(rect.width),
                displayHeight: Math.round(rect.height),
                aboveFold: rect.top < window.innerHeight,
                loading: img.loading || 'default'
            };
        });

        // Font sizes
        const textEls = [...document.querySelectorAll('p, span, li, a, h1, h2, h3')].slice(0, 30);
        const fontSizes = textEls.map(el => {
            const cs = window.getComputedStyle(el);
            return parseFloat(cs.fontSize);
        }).filter(s => s > 0);
        result.minFontSize = fontSizes.length ? Math.min(...fontSizes) : null;
        result.avgFontSize = fontSizes.length ? (fontSizes.reduce((a,b)=>a+b,0)/fontSizes.length).toFixed(1) : null;

        // Touch targets (links and buttons)
        const touchEls = [...document.querySelectorAll('a, button, input, select, textarea')].slice(0, 50);
        const smallTargets = touchEls.filter(el => {
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && (rect.width < 48 || rect.height < 48);
        }).map(el => {
            const rect = el.getBoundingClientRect();
            return {
                tag: el.tagName,
                text: (el.innerText || '').trim().substring(0, 50),
                width: Math.round(rect.width),
                height: Math.round(rect.height)
            };
        });
        result.smallTouchTargets = smallTargets;
        result.totalInteractive = touchEls.length;

        // Horizontal overflow check
        result.pageWidth = document.documentElement.scrollWidth;
        result.viewportWidth = window.innerWidth;
        result.hasHorizontalScroll = document.documentElement.scrollWidth > window.innerWidth + 5;

        // Body computed styles
        const body = document.body;
        const bodyCS = window.getComputedStyle(body);
        result.bodyFontSize = bodyCS.fontSize;

        // Check for flexbox/grid usage
        const allEls = [...document.querySelectorAll('*')].slice(0, 200);
        let flexCount = 0, gridCount = 0;
        allEls.forEach(el => {
            const d = window.getComputedStyle(el).display;
            if (d === 'flex' || d === 'inline-flex') flexCount++;
            if (d === 'grid' || d === 'inline-grid') gridCount++;
        });
        result.flexboxUsage = flexCount;
        result.gridUsage = gridCount;

        // Hero section analysis
        const hero = document.querySelector('[class*="hero"], [class*="banner"], [class*="slider"], [class*="jumbotron"], .elementor-section-wrap > .elementor-section:first-child, .wp-block-cover');
        result.hasHeroSection = !!hero;
        if (hero) {
            const rect = hero.getBoundingClientRect();
            result.heroHeight = Math.round(rect.height);
            result.heroWidth = Math.round(rect.width);
        }

        return result;
    }""")
    return data

with sync_playwright() as p:
    browser = p.chromium.launch()
    all_results = {}

    for page_name, url in PAGES:
        all_results[page_name] = {}
        for vp_name, w, h in VIEWPORTS:
            print(f"Capturing {page_name} @ {vp_name} ({w}x{h})...")
            context = browser.new_context(
                viewport={'width': w, 'height': h},
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1' if vp_name == 'mobile' else 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            try:
                page.goto(url, wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(2000)  # let animations settle

                # Above the fold screenshot
                fname = f"{page_name}_{vp_name}_above_fold.png"
                page.screenshot(path=os.path.join(SCREENSHOT_DIR, fname), full_page=False)

                # Full page screenshot
                fname_full = f"{page_name}_{vp_name}_full.png"
                page.screenshot(path=os.path.join(SCREENSHOT_DIR, fname_full), full_page=True)

                # Analysis
                data = analyze_page(page, page_name, vp_name)
                all_results[page_name][vp_name] = data

            except Exception as e:
                print(f"  ERROR: {e}")
                all_results[page_name][vp_name] = {"error": str(e)}
            finally:
                context.close()

    browser.close()

# Save results
with open(os.path.join(SCREENSHOT_DIR, "analysis_results.json"), "w") as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

print("\nDone! Results saved.")
