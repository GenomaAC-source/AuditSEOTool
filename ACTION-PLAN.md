# SEO Action Plan: ambito.it

**Date:** 2026-03-24
**Current Score:** 42/100 (Poor)
**Target Score:** 75+ (Good) within 3 months

---

## CRITICAL PRIORITY (Fix Immediately -- Week 1)

These issues block indexing, harm rankings, or cause penalties.

### C1. Disable Autoptimize CSS Inlining
- **Location:** WordPress Admin > Autoptimize > CSS Options
- **Action:** Uncheck "Inline all CSS" option
- **Impact:** Reduces HTML payload from ~1.6 MB to ~200 KB per page. Single biggest performance improvement possible.
- **Effort:** 5 minutes
- **Expected improvement:** Lighthouse +20-30 points, LCP -2-3 seconds

### C2. Fix Hero Image Lazy Loading
- **Location:** ShortPixel Adaptive Images settings
- **Action:** Exclude above-the-fold hero images from lazy loading. Remove `data-src` pattern for LCP images. Ensure `fetchpriority="high"` works with actual image URL in `src`.
- **Impact:** LCP improvement of 2-4 seconds
- **Effort:** 30 minutes

### C3. Fix Mixed Content (HTTP to HTTPS)
- **Location:** WordPress Admin > Settings > General
- **Action:** Ensure both WordPress Address and Site Address use `https://`. Run search-and-replace in database for remaining `http://ambito.it` references.
- **Impact:** Fixes 181 broken image references in sitemaps, fixes Organization schema URL, eliminates mixed content warnings.
- **Effort:** 1 hour

### C4. Fix Base Font Size
- **Location:** Theme CSS / Customizer
- **Action:** Change base font size from 11px to 16px minimum
- **Impact:** Passes Google mobile usability test, improves readability for all users
- **Effort:** 30 minutes

### C5. Fix Duplicate H1 Tags
- **Location:** Elementor templates for all page types
- **Action:** Ensure each page has exactly one H1 tag. Change secondary headings to H2. Make H1 visible (remove `visibility: false`).
- **Impact:** Correct heading hierarchy for crawlers and accessibility
- **Effort:** 2-3 hours across templates

---

## HIGH PRIORITY (Fix Within 1 Week)

These significantly impact rankings.

### H1. Upgrade PHP Version
- **Location:** IONOS hosting panel
- **Action:** Upgrade from PHP 7.4.33 to PHP 8.2+
- **Impact:** 20-40% faster server response times + security patches
- **Effort:** 1 hour (test compatibility first)

### H2. Change max-image-preview to "large"
- **Location:** Rank Math > General Settings > Global Meta
- **Action:** Set `max-image-preview` to `large` for all content pages/posts
- **Impact:** Enables Google Discover eligibility for visual content
- **Effort:** 5 minutes

### H3. Enable BreadcrumbList Schema
- **Location:** Rank Math > General Settings > Breadcrumbs
- **Action:** Enable breadcrumb schema output
- **Impact:** Rich breadcrumb snippets in search results
- **Effort:** 5 minutes

### H4. Fix Homepage Schema Type
- **Location:** Rank Math > Edit Page (Homepage)
- **Action:** Change schema type from `AboutPage` to `WebPage`. Set /chi-siamo/ as `AboutPage`.
- **Impact:** Correct semantic signaling to search engines
- **Effort:** 10 minutes

### H5. Add SoftwareApplication Schema to Product Pages
- **Location:** Rank Math > Edit Page (each product page)
- **Action:** Add `SoftwareApplication` schema to WebSIT, SUAPNet, Mosaico DigitAI, Servizi Cimiteriali pages
- **Impact:** Rich results eligibility for software products
- **Effort:** 1-2 hours (use JSON-LD templates from schema-audit-ambito.md)

### H6. Add CTA Above the Fold on Homepage
- **Location:** Elementor > Homepage template
- **Action:** Add a prominent CTA button ("Richiedi una Demo" or "Scopri le Soluzioni") in the hero section, visible without scrolling
- **Impact:** Improved conversion rate, better engagement signals
- **Effort:** 30 minutes

### H7. Add Blog Post Heading Structure
- **Location:** Each blog post content
- **Action:** Add H2/H3 subheadings to break up content. Minimum 3-4 H2s per post.
- **Impact:** Better content structure for crawlers and readability
- **Effort:** 15 minutes per post (prioritize recent/high-traffic posts)

### H8. Remove Render-Blocking Google Fonts
- **Location:** Theme or plugin settings
- **Action:** Self-host Montserrat font with `font-display: swap`. Add `<link rel="preconnect" href="https://fonts.googleapis.com">` if external loading is kept.
- **Impact:** Faster First Contentful Paint
- **Effort:** 1 hour

### H9. Limit reCAPTCHA to Contact Pages Only
- **Location:** reCAPTCHA plugin settings
- **Action:** Load reCAPTCHA script only on pages with forms, not site-wide
- **Impact:** Removes unnecessary JavaScript from 95% of pages
- **Effort:** 30 minutes

---

## MEDIUM PRIORITY (Fix Within 1 Month)

These are optimization opportunities.

### M1. Expand Content Depth on Key Pages
- **Pages:** Servizi Cimiteriali (287 words), blog posts (300-500 words avg)
- **Action:** Expand product pages to 800+ words with features, benefits, use cases, FAQs. Expand blog posts to 1,000+ words with subheadings, data, examples.
- **Target:** At least 5 key pages expanded per week
- **Effort:** 2-4 hours per page

### M2. Add Author Bios to Blog Posts
- **Action:** Create author profile pages with credentials, experience, photo. Display author bio at bottom of each post.
- **Impact:** E-E-A-T signal for expertise
- **Effort:** 2 hours setup + 30 min per author

### M3. Add Quantified Social Proof
- **Action:** Add municipality count, years of service, client logos, case study metrics across homepage and product pages
- **Impact:** Authoritativeness and trust signals
- **Effort:** 2-3 hours

### M4. Add Security Headers
- **Headers to add:** Content-Security-Policy, X-Content-Type-Options, Referrer-Policy
- **Location:** .htaccess or IONOS server config
- **Effort:** 1 hour

### M5. Optimize Elementor Plugin Stack
- **Action:** Audit and remove unused Elementor addon plugins (Royal, Happy, Essential, Exclusive). Keep only what's actively used.
- **Impact:** Significant reduction in JavaScript payload
- **Effort:** 2-4 hours (careful testing required)

### M6. Implement Page Caching
- **Action:** Enable server-side page caching via IONOS or WP caching plugin (WP Super Cache, W3 Total Cache, or LiteSpeed Cache)
- **Impact:** TTFB reduction from 1.4s to <0.5s
- **Effort:** 1-2 hours

### M7. Add srcset/sizes to Images
- **Action:** Ensure all images use responsive `srcset` and `sizes` attributes
- **Impact:** Appropriate image sizes served per device
- **Effort:** 2-3 hours

### M8. Fix Footer Alt Text
- **Action:** Add descriptive alt text to 2 certification badge images in footer
- **Impact:** Accessibility compliance, minor image SEO
- **Effort:** 10 minutes

### M9. Add Cross-Linking Between Related Content
- **Action:** Link blog posts to related product pages and vice versa. Link related blog posts to each other.
- **Impact:** Better internal link equity distribution, improved crawl depth
- **Effort:** 1-2 hours

### M10. Fix Logo Lazy Loading
- **Action:** Remove `loading="lazy"` from site logo (it's always above the fold)
- **Impact:** Faster logo rendering, minor LCP improvement
- **Effort:** 10 minutes

---

## LOW PRIORITY (Backlog)

Nice to have improvements.

### L1. Add /.well-known/llms.txt
- **Action:** Create a mirror of `/llms.txt` at `/.well-known/llms.txt`
- **Effort:** 10 minutes

### L2. Add Explicit AI Crawler Directives to robots.txt
- **Action:** Add `User-agent: GPTBot`, `User-agent: ClaudeBot`, etc. with explicit Allow directives. Consider blocking CCBot and anthropic-ai (training-only bots).
- **Effort:** 15 minutes

### L3. Create FAQ Sections on Product Pages
- **Action:** Add structured FAQ content to product pages with FAQ schema markup
- **Impact:** AI citation readiness, possible FAQ rich results
- **Effort:** 1-2 hours per page

### L4. Add Video Sitemap
- **Action:** If `/raccolta-video/` page has video content, create a video sitemap
- **Effort:** 1 hour

### L5. Review Stale Content
- **Action:** Update or consolidate old blog posts (e.g., COVID-19 mask distribution module, 2021 content)
- **Effort:** Variable

### L6. Improve Touch Target Sizes
- **Action:** Increase hamburger menu, search icon, and breadcrumb link sizes to minimum 48x48px
- **Effort:** 1 hour

### L7. Fix Cookie Banner Dismiss Button Size
- **Action:** Increase cookie consent dismiss button to minimum 44x44px
- **Effort:** 15 minutes

---

## IMPLEMENTATION TIMELINE

### Week 1 (Critical)
- [ ] C1: Disable Autoptimize CSS inlining
- [ ] C2: Fix hero image lazy loading
- [ ] C3: Fix HTTP to HTTPS mixed content
- [ ] C4: Fix base font size to 16px
- [ ] C5: Fix duplicate/hidden H1 tags
- [ ] H1: Upgrade PHP to 8.2+
- [ ] H2: Change max-image-preview to large
- [ ] H3: Enable BreadcrumbList schema

### Week 2 (High)
- [ ] H4: Fix homepage schema type
- [ ] H5: Add SoftwareApplication schema to product pages
- [ ] H6: Add homepage CTA above fold
- [ ] H7: Add heading structure to top 10 blog posts
- [ ] H8: Fix Google Fonts loading
- [ ] H9: Limit reCAPTCHA to form pages

### Weeks 3-4 (Medium)
- [ ] M1: Expand content on 5 key pages
- [ ] M2: Add author bios
- [ ] M3: Add social proof metrics
- [ ] M4: Add security headers
- [ ] M5: Audit Elementor plugins
- [ ] M6: Implement page caching

### Month 2-3 (Medium + Low)
- [ ] M7-M10: Image srcset, footer alt, cross-linking, logo lazy
- [ ] L1-L7: AI/GEO improvements, FAQ schema, content cleanup
- [ ] Continue expanding content depth

---

## EXPECTED SCORE PROGRESSION

| Timeframe | Expected Score | Key Drivers |
|-----------|---------------|-------------|
| Current | 42/100 | - |
| After Week 1 | 55-60/100 | Performance fixes (+15), mobile fixes (+5) |
| After Week 2 | 62-68/100 | Schema (+5), on-page (+5) |
| After Month 1 | 68-75/100 | Content expansion (+5), caching (+3) |
| After Month 3 | 75-82/100 | Full content strategy, GEO improvements |

---

*Generated by Claude SEO Audit System on 2026-03-24*
