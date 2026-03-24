# Core Web Vitals & Performance Audit: ambito.it

**Date:** 2026-03-24
**Auditor:** Claude Code (Web Performance Analysis)
**Method:** HTML source analysis, HTTP header inspection, resource inventory (PSI API quota exhausted)
**Site:** WordPress 6.9.1 on IONOS, Elementor Pro 3.35, Customizr theme 4.4.24, PHP 7.4.33

---

## Executive Summary

ambito.it has **critical performance problems** that will result in failing Core Web Vitals across all three metrics. The single most damaging issue is that **Autoptimize is inlining approximately 1.5 MB of CSS directly into every HTML document**, bloating each page to 1.5-1.9 MB of HTML alone. This makes the site effectively unoptimizable for LCP without addressing this root cause first.

**Estimated Lighthouse Performance Score: 15-30 (mobile), 40-55 (desktop)**

---

## 1. Server & Network Layer

### 1.1 TTFB (Time to First Byte)

| Metric | Measured | Target | Status |
|--------|----------|--------|--------|
| TTFB (avg of 3 runs) | **1,443 ms** | < 800 ms | FAIL |
| DNS Lookup | 1.8 ms | < 50 ms | PASS |
| TCP Connect | 82 ms | < 100 ms | PASS |
| Server Processing | ~1,350 ms | < 600 ms | FAIL |

**Severity: HIGH**

Root causes:
- **PHP 7.4.33** is running -- this version reached end of life in November 2022. PHP 8.2+ provides 20-40% faster execution.
- No server-side page cache detected (no `x-cache`, `cf-cache-status`, or similar headers).
- IONOS shared hosting likely contributes to inconsistent server response times (1.2s-1.6s range observed).
- The server must generate 1.5-1.9 MB of HTML per request, which is extremely expensive.

### 1.2 HTTP Headers & Compression

| Check | Result |
|-------|--------|
| HTTP/2 | Yes |
| Gzip compression | Yes (HTML only verified) |
| Brotli compression | Not detected |
| Cache-Control headers | Not present on HTML |
| ETag | Not present |
| CDN | None detected |
| Early Hints (103) | Not present |

**Severity: MEDIUM** -- No CDN, no Brotli, no cache headers on HTML responses.

---

## 2. Core Web Vitals Assessment

### 2.1 LCP (Largest Contentful Paint) -- ESTIMATED: 5.0-8.0s mobile / 3.0-5.0s desktop

**Status: POOR (> 4.0s threshold)**

The LCP element on the homepage is the hero image:
```
Ambito-Srl_Servizi-per-la-Pubblica-Amministrazione-1024x683.png (274 KB)
```

**Critical LCP chain:**
1. Browser requests HTML -- **1.4s TTFB**
2. Browser must parse **1.5 MB of inline CSS** before reaching body content
3. Hero image `src` is a **transparent GIF placeholder** (`data:image/gif;base64,R0lGOD...`)
4. Actual image URL is in `data-src` -- requires **ShortPixel Adaptive JS** to execute
5. ShortPixel JS must load, execute, detect the element, then start the image fetch
6. Image loads from `sp-ao.shortpixel.ai` (no preconnect hint)

**This is a catastrophic LCP chain.** The hero image cannot even begin loading until:
- 1.5 MB of inline CSS is parsed
- The DOM is built
- ShortPixel's JavaScript executes
- JS swaps `data-src` to `src`

The `fetchpriority="high"` attribute is present but **completely ineffective** because the real image URL is hidden behind `data-src`. The browser's preload scanner cannot discover it.

Additionally, the `fetchpriority="high"` attribute is duplicated (`fetchpriority="high" fetchpriority="high"`), which is a minor code quality issue.

### 2.2 INP (Interaction to Next Paint) -- ESTIMATED: 300-600ms mobile

**Status: POOR (> 200ms threshold)**

Contributing factors:
- **89 script tags** on the homepage (37 external JS files + 52 inline scripts)
- Multiple heavy Elementor addon libraries competing for main thread time:
  - Elementor core + Pro
  - Royal Elementor Addons (with parallax/jarallax)
  - Happy Elementor Addons
  - Essential Addons for Elementor Lite
  - Exclusive Addons for Elementor
- jQuery + jQuery Migrate still loaded (legacy dependency)
- Google reCAPTCHA loaded on every page (not just forms)
- MonsterInsights (Google Analytics plugin) with its own frontend JS
- 1.5 MB of inline CSS that must be parsed before any interaction is possible

### 2.3 CLS (Cumulative Layout Shift) -- ESTIMATED: 0.05-0.15

**Status: NEEDS IMPROVEMENT to POOR**

Positive findings:
- All `<img>` tags have `width` and `height` attributes (good)
- Images use `decoding="async"` (good)

Risk factors:
- Google Fonts (Montserrat) loaded via render-blocking `<link>` stylesheet with no `font-display` control
- 13 `@font-face` declarations inline (icon fonts: Font Awesome 5, eicons, Happy Icons, Exclusive Icons, slick, WooCommerce, etc.)
- ShortPixel lazy-loading swaps placeholder GIFs for real images, which can cause layout shifts if dimensions mismatch
- Cookie consent banner (CookieLawInfo) injects content dynamically
- Royal Elementor Addons modal popups script loaded on every page

---

## 3. Per-Page Analysis

| Page | HTML Size | Inline CSS | Scripts | Images | TTFB | Download Time |
|------|-----------|------------|---------|--------|------|---------------|
| Homepage | 1.66 MB | 1.52 MB (91%) | 89 | 9 | 1.20s | 1.90s |
| Chi Siamo | 1.71 MB | 1.59 MB (93%) | 53 | 8 | 1.29s | 2.04s |
| Suite Mosaico DigitAI | 1.91 MB | 1.78 MB (93%) | 53 | 9 | 1.26s | 6.48s |
| WebSIT | 1.67 MB | 1.50 MB (90%) | 91 | 5 | 1.23s | 2.60s |
| Contatti | 1.50 MB | 1.41 MB (94%) | 53 | 5 | 1.41s | 2.99s |

**Key observation:** Inline CSS accounts for 90-94% of every HTML document. The Suite Mosaico page took 6.48 seconds to fully download, which is the worst case.

---

## 4. Resource Inventory

### 4.1 JavaScript (37 external files + inline)

| Category | Files | Examples |
|----------|-------|---------|
| WordPress Core | 8 | jquery 3.7.1, jquery-migrate, underscore, backbone, wp-hooks, wp-i18n, imagesloaded, comment-reply |
| Elementor Core | 4 | webpack.runtime, frontend-modules, frontend, font-awesome v4-shims |
| Elementor Pro | 3 | webpack-pro.runtime, frontend, elements-handlers |
| Royal Elementor Addons | 5 | jarallax, parallax, dompurify, frontend, modal-popups |
| Happy Elementor Addons | 3 | dom-purify, reading-progress-bar, happy-addons |
| Essential Addons | 1 | general.min.js |
| Exclusive Addons | 1 | exad-scripts.min.js |
| Autoptimize Bundles | 6 | Various combined/minified bundles |
| Analytics | 1 | MonsterInsights frontend-gtag |
| Third-Party | 2 | Google reCAPTCHA, Google Tag Manager |
| Theme | 2 | Customizr tc-init, modernizr |

**DOMPurify is loaded TWICE** -- once by Happy Elementor Addons and once by Royal Elementor Addons.

### 4.2 CSS

All CSS has been inlined by Autoptimize into the HTML `<style>` blocks. There are also 4 Autoptimize CSS cache files referenced elsewhere. The inline CSS contains styles for:
- Full Customizr theme stylesheet
- Full Elementor base + Pro styles
- 5 different Elementor addon plugin stylesheets
- Font Awesome 5 (complete icon set)
- Multiple icon font families
- WooCommerce styles (site does not appear to use WooCommerce as a store)
- Cookie Law Info styles
- Ninja Forms styles
- GDPR cookie consent table markup embedded inside CSS (!)

### 4.3 Images

- All 9 images on the homepage are PNG format
- ShortPixel Adaptive converts to WebP on-the-fly via CDN proxy
- Hero image: 274 KB (1024x683) -- could be significantly smaller in AVIF
- Logo: 9 KB (reasonable)
- Blog post thumbnails: 300px wide, loaded via ShortPixel

### 4.4 Fonts

| Font | Loading Method | Impact |
|------|---------------|--------|
| Montserrat (400,700,900) | Google Fonts `<link>` stylesheet (render-blocking) | HIGH -- blocks rendering |
| Font Awesome 5 Free | @font-face inline (woff2/woff/ttf) | MEDIUM -- icon font |
| Font Awesome 5 Brands | @font-face inline | LOW |
| eicons (Elementor) | @font-face inline | LOW |
| Happy Icons | @font-face inline | LOW |
| Exclusive Icons | @font-face inline | LOW |
| slick | @font-face inline | LOW |
| WooCommerce | @font-face inline | LOW (unnecessary) |
| Customizr | Preloaded woff2 | GOOD |
| lg (lightGallery) | @font-face inline | LOW |

Only the Customizr theme font is properly preloaded. Montserrat from Google Fonts is fully render-blocking.

### 4.5 Third-Party Scripts

| Service | Domain | Impact |
|---------|--------|--------|
| Google reCAPTCHA | www.google.com/recaptcha | HIGH -- loaded on every page, not just contact form |
| Google Tag Manager | www.googletagmanager.com | MEDIUM |
| ShortPixel Adaptive | sp-ao.shortpixel.ai | HIGH -- controls LCP image loading |

---

## 5. WordPress Plugin Audit (Performance Impact)

| Plugin | Purpose | Performance Impact | Recommendation |
|--------|---------|-------------------|----------------|
| Elementor + Pro 3.35 | Page builder | HIGH -- heavy CSS/JS | Keep but optimize asset loading |
| Royal Elementor Addons | Extra widgets | HIGH -- parallax, popups JS on every page | Remove if not actively used |
| Happy Elementor Addons | Extra widgets | MEDIUM -- reading progress bar, custom JS | Remove if not actively used |
| Essential Addons Lite | Extra widgets | MEDIUM -- general.min.js on every page | Remove if not actively used |
| Exclusive Addons | Extra widgets | MEDIUM -- JS + icon font on every page | Remove if not actively used |
| Autoptimize | CSS/JS optimization | **CRITICAL NEGATIVE** -- inlining 1.5 MB CSS | Reconfigure or replace |
| ShortPixel Adaptive | Image CDN/WebP | HIGH NEGATIVE for LCP -- lazy-loads hero image | Exclude above-fold images |
| MonsterInsights | Analytics | LOW-MEDIUM | Consider lightweight alternative |
| Cookie Law Info | GDPR consent | LOW | Acceptable |
| Ninja Forms | Contact forms | LOW | Acceptable |
| Colorlib 404 | Custom 404 page | NEGLIGIBLE | Acceptable |
| Rank Math | SEO | NEGLIGIBLE | Acceptable |

**Critical finding:** The site runs **4 different Elementor addon plugins** simultaneously. This is extremely unusual and strongly suggests that different widgets were needed from each, but the cumulative cost is severe.

---

## 6. Prioritized Recommendations

### CRITICAL (Expected impact: +30-50 Lighthouse points)

#### C1. Fix Autoptimize CSS Inlining Configuration
**Current state:** Autoptimize is inlining ALL CSS (~1.5 MB) into every HTML document.
**Action:** In Autoptimize settings:
1. Uncheck "Inline all CSS" -- this is the single most impactful change
2. Enable "Aggregate CSS files" instead (external cached file)
3. Use "Inline and Defer CSS" with only critical above-the-fold CSS (~15-20 KB) inlined
4. Expected HTML size reduction: **~1.4 MB per page** (from 1.6 MB to ~200 KB)
**Impact on CWV:** LCP improvement of 1-3 seconds (parser no longer blocked by 1.5 MB inline CSS), TTFB improvement (smaller response), INP improvement (less CSS parsing work)

#### C2. Fix Hero Image Lazy Loading (LCP Element)
**Current state:** ShortPixel Adaptive replaces the hero image `src` with a transparent GIF placeholder and puts the real URL in `data-src`. This makes the LCP image invisible to the browser's preload scanner.
**Action:**
1. Exclude above-the-fold images from ShortPixel lazy loading (ShortPixel settings > Exclusions)
2. Add a `<link rel="preload">` for the hero image in the `<head>`:
   ```html
   <link rel="preload" as="image" href="https://ambito.it/wp-content/uploads/2025/11/Ambito-Srl_Servizi-per-la-Pubblica-Amministrazione-1024x683.png" type="image/png" fetchpriority="high">
   ```
3. Remove the duplicate `fetchpriority="high"` attribute
**Impact on CWV:** LCP improvement of 2-4 seconds (image discovery moves from after-JS-execution to preload-scanner phase)

#### C3. Upgrade PHP Version
**Current state:** PHP 7.4.33 (EOL since November 2022 -- also a security risk).
**Action:** Upgrade to PHP 8.2 or 8.3 via IONOS hosting panel. Test in staging first.
**Impact on CWV:** TTFB improvement of 20-40% (from ~1.4s to ~0.8-1.0s). Also improves security posture.

### HIGH (Expected impact: +10-20 Lighthouse points)

#### H1. Consolidate or Remove Redundant Elementor Addons
**Current state:** 4 separate Elementor addon plugins (Royal, Happy, Essential, Exclusive) each loading their own CSS and JS on every page.
**Action:**
1. Audit which widgets from each addon are actually used on the site
2. Keep only the one addon that provides the most needed widgets
3. Remove the rest -- this will eliminate 3-4 JS files and significant CSS per page
**Impact on CWV:** INP improvement (less JS to parse), LCP improvement (less CSS), reduced HTML size

#### H2. Implement Server-Side Page Caching
**Current state:** No page cache detected. Every request hits PHP/MySQL.
**Action:** Install WP Super Cache or W3 Total Cache (or use IONOS built-in caching if available). Configure:
- Page cache enabled
- Browser caching headers (Cache-Control, Expires)
- Object cache if available (Redis/Memcached)
**Impact on CWV:** TTFB improvement to < 500ms for cached pages

#### H3. Fix Google Fonts Loading
**Current state:** Montserrat loaded via render-blocking `<link>` stylesheet from fonts.googleapis.com.
**Action:**
1. Self-host Montserrat font files (woff2 only, subset to Latin + Latin Extended)
2. Use `font-display: swap` in the @font-face declaration
3. Preload the most critical weight (400):
   ```html
   <link rel="preload" as="font" type="font/woff2" href="/fonts/montserrat-v26-latin-regular.woff2" crossorigin>
   ```
4. Remove the Google Fonts stylesheet link
**Impact on CWV:** LCP improvement of 200-500ms, CLS improvement (controlled font swap), eliminates a render-blocking request + DNS lookup to fonts.googleapis.com + fonts.gstatic.com

#### H4. Restrict reCAPTCHA to Contact Page Only
**Current state:** Google reCAPTCHA API loaded on every page.
**Action:** Conditionally load reCAPTCHA only on pages with forms (e.g., /contatti/). This can be done via:
- Ninja Forms settings (if it controls reCAPTCHA loading)
- A small code snippet in functions.php to dequeue the script on non-form pages
**Impact on CWV:** INP improvement on non-form pages (eliminates third-party JS execution), LCP improvement (one fewer blocking resource chain)

### MEDIUM (Expected impact: +5-10 Lighthouse points)

#### M1. Implement a CDN
**Current state:** All assets served directly from IONOS origin server in Europe.
**Action:** Implement Cloudflare (free tier) or similar CDN. Benefits:
- Edge caching for static assets globally
- Brotli compression (currently only gzip)
- HTTP/3 support
- Automatic minification
- Page rules for cache headers
**Impact on CWV:** TTFB improvement for non-EU visitors, overall faster asset delivery

#### M2. Remove Unused CSS/JS
**Current state:** WooCommerce CSS loaded despite no store functionality. Multiple icon fonts loaded when likely only Font Awesome is needed.
**Action:**
1. If WooCommerce is not used, remove it entirely
2. Use Asset CleanUp or Perfmatters plugin to conditionally disable unused CSS/JS per page
3. Remove Font Awesome v4-shims.min.js if no legacy FA4 icons are used
**Impact on CWV:** Reduced CSS/JS parse time, smaller payloads

#### M3. Convert Hero Image to AVIF/WebP with Proper Sizing
**Current state:** Hero image is 274 KB PNG (1024x683). ShortPixel converts to WebP on-the-fly but adds latency through its proxy.
**Action:**
1. Generate AVIF and WebP versions at build time
2. Use `<picture>` element with `<source>` for AVIF, WebP, PNG fallback
3. Serve directly from origin (no ShortPixel proxy for above-fold images)
4. Expected size: ~40-60 KB in AVIF vs 274 KB PNG
**Impact on CWV:** LCP improvement of 200-500ms (smaller file, no proxy hop)

#### M4. Add Preconnect Hints
**Current state:** No `<link rel="preconnect">` hints present.
**Action:** Add preconnect for critical third-party origins:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://www.googletagmanager.com">
```
(If Google Fonts remain external after H3)
**Impact on CWV:** LCP improvement of 100-300ms per preconnected origin

### LOW (Expected impact: +2-5 Lighthouse points)

#### L1. Remove jQuery Migrate
**Action:** If no legacy jQuery code depends on it, dequeue jquery-migrate. WordPress 6.9 does not require it.

#### L2. Add Cache-Control Headers for Static Assets
**Action:** Configure `.htaccess` for long-lived caching:
```apache
<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresByType image/webp "access plus 1 year"
  ExpiresByType image/png "access plus 1 year"
  ExpiresByType text/css "access plus 1 year"
  ExpiresByType application/javascript "access plus 1 year"
  ExpiresByType font/woff2 "access plus 1 year"
</IfModule>
```

#### L3. Implement `103 Early Hints`
**Action:** If IONOS supports it, configure Early Hints to preload critical resources before the full HTML response is ready.

---

## 7. Impact Projection

| Scenario | Est. Mobile LCP | Est. Mobile INP | Est. CLS | Est. Lighthouse |
|----------|----------------|-----------------|----------|-----------------|
| Current state | 5.0-8.0s | 300-600ms | 0.05-0.15 | 15-30 |
| After C1 + C2 + C3 | 2.5-4.0s | 200-400ms | 0.05-0.10 | 45-60 |
| After all Critical + High | 1.8-3.0s | 150-250ms | 0.02-0.08 | 60-75 |
| After all recommendations | 1.5-2.5s | 100-200ms | 0.01-0.05 | 75-90 |

---

## 8. Immediate Action Plan (Priority Order)

1. **Today:** Reconfigure Autoptimize -- stop inlining all CSS (C1)
2. **Today:** Exclude hero images from ShortPixel lazy loading (C2)
3. **This week:** Upgrade PHP to 8.2+ (C3)
4. **This week:** Install page caching plugin (H2)
5. **This week:** Self-host Google Fonts with font-display:swap (H3)
6. **Next week:** Audit and remove redundant Elementor addons (H1)
7. **Next week:** Restrict reCAPTCHA to form pages (H4)
8. **Next sprint:** Implement CDN (M1)
9. **Next sprint:** Remove unused CSS/JS (M2)
10. **Next sprint:** Optimize hero image format (M3)

---

## Notes

- This analysis was performed via HTML source inspection and HTTP timing. For precise Core Web Vitals field data, check [CrUX Vis](https://cruxvis.withgoogle.com) for ambito.it (if sufficient traffic data exists).
- The PageSpeed Insights API quota was exhausted during testing. Re-run with a PSI API key for lab-measured Lighthouse scores.
- All TTFB measurements were taken from a non-EU location; Italian users on IONOS EU servers will see better TTFB (~200-400ms reduction expected).
- INP can only be accurately measured with real user interaction data (CrUX) or manual testing with Chrome DevTools Performance panel.
