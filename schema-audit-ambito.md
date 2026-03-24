# Schema.org Structured Data Audit -- ambito.it

**Audit date:** 2026-03-24
**Tool detected:** Rank Math SEO (WordPress plugin)
**Format in use:** JSON-LD via @graph pattern (correct approach)

---

## 1. PAGE-BY-PAGE DETECTION AND VALIDATION

### 1.1 Homepage -- https://ambito.it/

**Detected schema types (JSON-LD):**

| @type | @id | Status |
|---|---|---|
| Place | `#place` | Present |
| Organization | `#organization` | Present |
| WebSite | `#website` | Present |
| ImageObject | (primary image) | Present |
| AboutPage | `#webpage` | WRONG TYPE |

**Validation issues:**

| # | Severity | Issue | Detail |
|---|---|---|---|
| 1 | Critical | **Homepage typed as AboutPage** | The homepage `@type` is `AboutPage` instead of `WebPage` or a custom homepage type. The "About" page (`/chi-siamo/`) is the actual about page. This mistyping can confuse Google about the site's primary page. Fix in Rank Math > Titles & Meta > Homepage > Schema Type. |
| 2 | Critical | **Organization URL uses http** | `"url": "http://ambito.it"` should be `"https://ambito.it"` (with trailing slash ideally matching canonical). This mismatch appears on every single page since the Organization block is site-wide. |
| 3 | Medium | **Missing sameAs for YouTube and LinkedIn** | Only Facebook is listed. The site footer links to YouTube (`youtube.com/@ambito3167`). If LinkedIn exists, it should also be included. |
| 4 | Medium | **ImageObject URLs use http** | `"url": "http://ambito.it/wp-content/uploads/..."` -- all ImageObject references use `http://` instead of `https://`. This appears across every page. |
| 5 | Low | **No BreadcrumbList schema** | The homepage naturally does not need breadcrumbs, but this becomes an issue on inner pages (see below). |
| 6 | Low | **addressCountry should use ISO code** | `"addressCountry": "Italia"` should be `"IT"` (ISO 3166-1 alpha-2) for maximum interoperability. |

---

### 1.2 Chi siamo -- https://ambito.it/chi-siamo/

**Detected schema types:**
- Place, Organization, WebSite (site-wide, same as homepage)
- WebPage (correct type for this page)
- Person (Stefania Bozzoli)
- Article

**Validation issues:**

| # | Severity | Issue |
|---|---|---|
| 1 | Medium | **Article type used for an About page** -- This is a static corporate page, not an article. The Article schema is inappropriate here. Should use only WebPage with `about` pointing to the Organization entity. |
| 2 | Medium | **No BreadcrumbList** -- Visual breadcrumb navigation exists on the page but is not marked up with BreadcrumbList schema. |
| 3 | Low | **Inherits all site-wide http URL issues** from section 1.1. |

---

### 1.3 Suite Mosaico DigitAI -- https://ambito.it/suite-mosaico-digitai/

**Detected schema types:**
- Place, Organization, WebSite (site-wide)
- WebPage
- Person (Stefania Bozzoli)
- Article

**Validation issues:**

| # | Severity | Issue |
|---|---|---|
| 1 | Critical | **No SoftwareApplication / Product schema** -- This is a product suite page. It should have `SoftwareApplication` or `Product` schema describing the suite, its features, and its category. This is the single biggest missed opportunity on the site. |
| 2 | Medium | **Article type used for a product page** -- Same issue as About page; this is not editorial content. |
| 3 | Medium | **No BreadcrumbList** -- Visual breadcrumbs present, schema absent. |

---

### 1.4 WebSIT -- https://ambito.it/websit-sistema-informativo-territoriale/

**Detected schema types:**
- Place, Organization, WebSite (site-wide)
- WebPage
- Person (Stefania Bozzoli)
- Article

**Validation issues:**

| # | Severity | Issue |
|---|---|---|
| 1 | Critical | **No SoftwareApplication schema** -- WebSIT is a named software product with a registered trademark. It absolutely should have dedicated SoftwareApplication markup with applicationCategory, operatingSystem, offers, etc. |
| 2 | Medium | **Article type used for a product page** -- Same inappropriate typing as above. |
| 3 | Medium | **No BreadcrumbList** -- Visual breadcrumbs present, schema absent. |

---

### 1.5 Contatti -- https://ambito.it/contatti/

**Detected schema types:**
- Place, Organization, WebSite (site-wide)
- ContactPage (correct type)

**Validation issues:**

| # | Severity | Issue |
|---|---|---|
| 1 | Low | **No BreadcrumbList** -- Visual breadcrumbs present. |
| 2 | Info | This is the cleanest page -- ContactPage is the correct type and no inappropriate Article schema is present. |

---

### 1.6 Blog Post -- https://ambito.it/proroga-bando-risorse-in-comune.../

**Detected schema types:**
- Place, Organization, WebSite (site-wide)
- WebPage
- Person (Stefania Bozzoli)
- Article

**Validation issues:**

| # | Severity | Issue |
|---|---|---|
| 1 | Medium | **Should be BlogPosting, not Article** -- The post is categorized under "Primo piano" and lives in the blog section. `BlogPosting` (a subtype of Article) is more semantically accurate and enables blog-specific rich result features. |
| 2 | Medium | **No BreadcrumbList** -- Visual breadcrumbs present. |
| 3 | Low | **Missing `articleBody`** -- Google recommends including `articleBody` or at least `wordCount` for Article/BlogPosting types. |
| 4 | Low | **Image dimensions 640x300** -- Google recommends images at least 1200px wide for Article rich results. |

---

### 1.7 Lavora con noi -- https://ambito.it/lavora-con-noi/

**Detected schema types:**
- Place, Organization, WebSite (site-wide)
- WebPage
- Person (Stefania Bozzoli)
- Article

**Validation issues:**

| # | Severity | Issue |
|---|---|---|
| 1 | Medium | **No JobPosting schema** -- If specific open positions are listed on the page, each should have `JobPosting` markup (title, description, datePosted, hiringOrganization, jobLocation, employmentType). This enables Google for Jobs rich results. |
| 2 | Medium | **Article type on a careers page** -- This is not editorial content. Should be WebPage only. |
| 3 | Medium | **No BreadcrumbList** -- Visual breadcrumbs present. |

---

## 2. SITE-WIDE ISSUES SUMMARY

These issues are injected by Rank Math on every page via the shared `@graph`:

| # | Severity | Issue | Fix Location |
|---|---|---|---|
| 1 | Critical | Organization `url` is `http://ambito.it` (no HTTPS, no trailing slash) | Rank Math > General Settings > Edit your knowledge graph URL |
| 2 | Critical | All ImageObject URLs use `http://` instead of `https://` | Rank Math may pull from WordPress Settings > General > Site Address. Ensure it uses https. Also run a search-replace on media URLs in the database. |
| 3 | Medium | No BreadcrumbList schema on any page despite visual breadcrumbs existing | Rank Math > General Settings > Breadcrumbs > Enable |
| 4 | Medium | `sameAs` only contains Facebook; missing YouTube, and potentially LinkedIn | Rank Math > Local SEO > Social Profiles |
| 5 | Medium | Article schema applied indiscriminately to static pages (About, Products, Careers) | Rank Math > Titles & Meta > Pages > Schema Type: set to "WebPage" for non-editorial pages, or configure per-page |
| 6 | Low | `addressCountry` uses "Italia" instead of ISO "IT" | Rank Math > Local SEO > Address |

---

## 3. MISSING SCHEMA OPPORTUNITIES

| Priority | Schema Type | Where | Benefit |
|---|---|---|---|
| **1 - HIGH** | SoftwareApplication | Each product page (WebSIT, SUAPNet, Mosaico DigitAI, cemetery software) | Enables Software rich results; critical for B2B SaaS discoverability |
| **2 - HIGH** | BreadcrumbList | All inner pages | Enables breadcrumb rich results in SERPs; already have visual breadcrumbs |
| **3 - HIGH** | BlogPosting (replace Article) | All blog posts | More semantically accurate; better blog-specific signals |
| **4 - MEDIUM** | JobPosting | Careers page (if specific positions exist) | Enables Google for Jobs rich results |
| **5 - MEDIUM** | Organization enhancement | Homepage / site-wide | Add `foundingDate`, `numberOfEmployees`, `description`, `areaServed`, additional `sameAs` |
| **6 - LOW** | FAQPage | Product pages with FAQ sections | Note: Google restricts FAQ rich results to government/healthcare. However, since Ambito serves Public Administration, the pages themselves may qualify in edge cases. More importantly, FAQPage markup benefits AI/LLM citation even without Google rich results. Recommend only if FAQ content actually exists on the pages. |

**Not recommended (per current Google guidelines):**
- HowTo: deprecated for rich results since September 2023
- SpecialAnnouncement: deprecated July 2025

---

## 4. READY-TO-USE JSON-LD -- TOP 3 MOST IMPACTFUL SCHEMAS

### 4.1 SoftwareApplication for WebSIT Product Page

Place this on: `https://ambito.it/websit-sistema-informativo-territoriale/`

```json
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "@id": "https://ambito.it/websit-sistema-informativo-territoriale/#software",
  "name": "WebSIT - Sistema Informativo Territoriale",
  "alternateName": "WebSIT",
  "description": "WebSIT e la piattaforma web per la gestione integrata del territorio. Digitalizza, analizza e condividi i dati comunali in modo sicuro e flessibile.",
  "url": "https://ambito.it/websit-sistema-informativo-territoriale/",
  "applicationCategory": "BusinessApplication",
  "applicationSubCategory": "Geographic Information System",
  "operatingSystem": "Web browser (cloud-based)",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "EUR",
    "description": "Contattaci per un preventivo personalizzato",
    "url": "https://ambito.it/contatti/",
    "availability": "https://schema.org/OnlineOnly"
  },
  "author": {
    "@id": "https://ambito.it/#organization"
  },
  "publisher": {
    "@id": "https://ambito.it/#organization"
  },
  "image": "https://ambito.it/wp-content/uploads/2023/08/WebSIT-logo.png",
  "featureList": "Gestione cartografica, Analisi territoriale, Integrazione dati catastali, Condivisione dati interoperabile, Accesso multi-utente sicuro",
  "audience": {
    "@type": "Audience",
    "audienceType": "Pubblica Amministrazione, Comuni italiani"
  },
  "inLanguage": "it-IT"
}
</script>
```

**Implementation note:** In Rank Math, go to the WebSIT page editor > Schema tab > Add Schema > Software Application, and fill in the fields. Alternatively, add the JSON-LD above via a custom code block or the Rank Math "Code" snippet feature. If using Rank Math's built-in schema, it will merge with the existing `@graph`. If adding manually, keep it as a separate `<script>` block.

**Important:** The `"price": "0"` with a description is a pattern Google accepts for "contact for pricing" B2B products. If you prefer, you can omit the `offers` block entirely, but having it increases the chance of rich result eligibility.

---

### 4.2 BreadcrumbList for All Inner Pages

This example is for the WebSIT product page. Adapt the `item` names and URLs for each page.

```json
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "@id": "https://ambito.it/websit-sistema-informativo-territoriale/#breadcrumb",
  "itemListElement": [
    {
      "@type": "ListItem",
      "position": 1,
      "name": "Home",
      "item": "https://ambito.it/"
    },
    {
      "@type": "ListItem",
      "position": 2,
      "name": "Soluzioni",
      "item": "https://ambito.it/suite-mosaico-digitai/"
    },
    {
      "@type": "ListItem",
      "position": 3,
      "name": "WebSIT - Sistema Informativo Territoriale"
    }
  ]
}
</script>
```

**Implementation note (recommended approach):** Enable breadcrumbs natively in Rank Math:
1. Go to Rank Math > General Settings > Breadcrumbs
2. Toggle "Enable Breadcrumbs" to ON
3. Rank Math will automatically generate BreadcrumbList JSON-LD matching your visible breadcrumb trail
4. This is far better than adding manual JSON-LD per page, since Rank Math will handle all 179 pages automatically

---

### 4.3 Enhanced Organization Schema (replace current site-wide block)

This replaces the existing Organization in Rank Math's settings. Configure via Rank Math > Local SEO and Rank Math > Titles & Meta > Global Meta > Knowledge Graph.

```json
{
  "@type": "Organization",
  "@id": "https://ambito.it/#organization",
  "name": "Ambito S.r.l.",
  "legalName": "Ambito S.r.l.",
  "url": "https://ambito.it/",
  "logo": {
    "@type": "ImageObject",
    "@id": "https://ambito.it/#logo",
    "url": "https://ambito.it/wp-content/uploads/2021/01/cropped-Logo-Ambito.png",
    "contentUrl": "https://ambito.it/wp-content/uploads/2021/01/cropped-Logo-Ambito.png",
    "caption": "Ambito S.r.l.",
    "inLanguage": "it-IT",
    "width": 550,
    "height": 161
  },
  "image": "https://ambito.it/wp-content/uploads/2021/01/cropped-Logo-Ambito.png",
  "description": "Ambito S.r.l. sviluppa soluzioni software innovative per la Pubblica Amministrazione italiana: sistemi informativi territoriali, sportelli unici digitali e piattaforme di gestione integrate.",
  "email": "info@ambito.it",
  "telephone": "+39-051-6861282",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "Via della Canapa 54",
    "addressLocality": "Cento",
    "addressRegion": "Emilia-Romagna",
    "postalCode": "44042",
    "addressCountry": "IT"
  },
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": 44.7267,
    "longitude": 11.2899
  },
  "contactPoint": [
    {
      "@type": "ContactPoint",
      "telephone": "+39-051-6861282",
      "contactType": "customer support",
      "availableLanguage": "Italian",
      "areaServed": "IT"
    }
  ],
  "sameAs": [
    "https://www.facebook.com/ambitosrl/",
    "https://www.youtube.com/@ambito3167"
  ],
  "areaServed": {
    "@type": "Country",
    "name": "IT"
  },
  "knowsAbout": [
    "Sistemi Informativi Territoriali",
    "Sportello Unico Attivita Produttive",
    "Digitalizzazione Pubblica Amministrazione",
    "Software per Comuni"
  ],
  "numberOfEmployees": {
    "@type": "QuantitativeValue",
    "value": "UPDATE_WITH_ACTUAL_NUMBER"
  },
  "foundingDate": "UPDATE_WITH_ACTUAL_YEAR",
  "location": {
    "@id": "https://ambito.it/#place"
  }
}
```

**Implementation notes:**
- Update `numberOfEmployees` and `foundingDate` with actual values
- Verify the `geo` coordinates (I estimated for Cento, FE -- confirm via Google Maps)
- The `telephone` now uses E.164 international format (`+39-051-6861282`)
- `addressCountry` now uses ISO 3166-1 code "IT"
- Add LinkedIn URL to `sameAs` if the company has a LinkedIn page
- Most of these fields can be configured directly in Rank Math > Local SEO

---

## 5. PRIORITIZED ACTION PLAN

### Immediate (Critical fixes -- do first)

1. **Fix Organization URL from http to https** -- Rank Math > General Settings or Local SEO > URL field. This affects every page on the site.
2. **Fix all ImageObject URLs from http to https** -- This likely requires updating WordPress Address (URL) in Settings > General, and potentially running a search-and-replace on the database (use the Better Search Replace plugin).
3. **Fix homepage schema type from AboutPage to WebPage** -- Rank Math > Titles & Meta > Homepage > Schema Type.

### Short-term (1-2 weeks)

4. **Enable BreadcrumbList in Rank Math** -- Single toggle, instant benefit across all 179 pages.
5. **Add SoftwareApplication schema to product pages** -- Start with WebSIT (highest-value product), then SUAPNet, then Mosaico DigitAI suite, then cemetery management software.
6. **Change blog post schema from Article to BlogPosting** -- Rank Math > Titles & Meta > Posts > Schema Type.
7. **Remove Article schema from static pages** -- For About, Product, and Careers pages, set schema to WebPage only.

### Medium-term (2-4 weeks)

8. **Enhance Organization schema** with description, foundingDate, numberOfEmployees, geo coordinates, additional sameAs profiles.
9. **Add JobPosting schema** to careers page if specific open positions are listed.
10. **Update addressCountry** from "Italia" to "IT" across all Place/PostalAddress blocks.
11. **Ensure blog post images are at least 1200px wide** for Article rich result eligibility.

---

## 6. RANK MATH CONFIGURATION CHECKLIST

Since the site uses Rank Math, most fixes can be made through its interface:

- [ ] Local SEO > Company URL: change to `https://ambito.it/`
- [ ] Local SEO > Address > Country: change to "IT"
- [ ] Local SEO > Social Profiles: add YouTube and LinkedIn URLs
- [ ] Local SEO > Coordinates: add latitude/longitude
- [ ] General Settings > Breadcrumbs: enable
- [ ] Titles & Meta > Homepage: change Schema Type from AboutPage to WebPage
- [ ] Titles & Meta > Posts: change Schema Type to BlogPosting
- [ ] Titles & Meta > Pages: ensure Schema Type is WebPage (not Article)
- [ ] Per product page: add SoftwareApplication schema via Schema tab in editor
- [ ] WordPress Settings > General: ensure Site URL uses https://
