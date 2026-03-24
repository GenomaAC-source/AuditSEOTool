# Visual and Mobile Rendering Analysis - ambito.it

**Analysis Date:** 2026-03-24
**Pages Analyzed:** 4 (Homepage, Chi Siamo, Suite Mosaico DigitAI, Contatti)
**Viewports Tested:** Mobile (375x812), Desktop (1280x800)

---

## Executive Summary

The ambito.it website (WordPress/Starter theme with Elementor) has a functional responsive layout that avoids horizontal scrolling, but suffers from critically small base font sizes, missing above-the-fold CTAs on the homepage, inconsistent H1 visibility, and multiple images lacking srcset/alt attributes. The site fundamentally works on mobile but has several medium-to-high severity issues that hurt both usability and SEO.

---

## CRITICAL ISSUES (Severity: HIGH)

### 1. Extremely Small Base Font Size (All Pages)
- **Body font size:** 11.0px (mobile) / 11.2px (desktop)
- **Minimum font detected:** 10.47px (mobile)
- **Google recommends:** 16px minimum base font for mobile readability
- **Impact:** Fails Core Web Vitals accessibility checks; users must pinch-to-zoom
- **Affected pages:** ALL

### 2. No Primary CTA Above the Fold on Homepage
- The homepage has NO business-related call-to-action visible above the fold on either mobile or desktop
- The "Parliamo del tuo progetto" (Talk about your project) CTA is located at top=1694px (mobile) and top=1111px (desktop) - far below the fold
- Only visible interactive elements above fold: navigation Search icon and cookie banner "Ok" button
- **Impact:** Visitors see a headline and image but no clear next step; high bounce risk

### 3. H1 Tags Invisible on 3 of 4 Pages
- **Chi Siamo:** H1 "Chi siamo" exists but `visible: false`
- **Suite Mosaico:** H1 "Suite Mosaico DigitAI" exists but `visible: false`
- **Contatti:** H1 "Contatti" exists but `visible: false`
- Only the Homepage H1 is visible
- **Impact:** Screen readers may detect them, but hidden H1s are a known SEO anti-pattern that Google may penalize

### 4. Logo Image Uses `loading="lazy"` Above the Fold
- The site logo (in the header) has `loading="lazy"`, which delays its rendering
- This applies to both viewport sizes across all pages
- **Impact:** Delays Largest Contentful Paint (LCP); Google recommends `loading="eager"` or removing the attribute for above-fold images

---

## MEDIUM ISSUES (Severity: MEDIUM)

### 5. Multiple Images Missing srcset/sizes Attributes
| Page | Images Missing srcset |
|------|----------------------|
| Homepage | 5 of 9 |
| Chi Siamo | 4 of 8 |
| Suite Mosaico | 6 of 9 |
| Contatti | 1 of 5 |

- **Impact:** Browser cannot select optimal image size per viewport; wastes bandwidth on mobile, potentially serves undersized images on desktop

### 6. Images Missing Alt Text
- 2 images per page (certification badge images in footer) have empty alt attributes
- **Impact:** Accessibility failure and missed SEO image indexing opportunity

### 7. Touch Targets Below 48x48px Minimum (Mobile)
- **Homepage mobile:** 4 undersized touch targets including:
  - Search icon: 35x45px
  - Hamburger menu: 40x40px
  - Logo link: 123x36px (height too small)
- **Desktop navigation links:** All at 36px height (below 48px minimum)
- **Impact:** Mobile usability issue flagged in Google Search Console

### 8. Cookie Banner Overlaps Content
- The cookie consent banner sits at the bottom of the viewport and covers content
- On the Suite Mosaico page, it visually overlaps the heading "Mosaico DigitAI: un solo sistema, infinite possibilita"
- The "Ok" button is small (41x31px) - below touch target minimum
- **Impact:** Content obscured; poor user experience

### 9. Breadcrumb Links Too Small on Mobile
- "Pagina iniziale" breadcrumb link measures only 69x14px on mobile
- Far below the 48px minimum touch target
- **Impact:** Difficult to tap on mobile; accessibility issue

---

## LOW ISSUES (Severity: LOW)

### 10. No CSS Grid Usage
- The site uses only Flexbox (36-37 instances) with zero CSS Grid usage
- While not inherently wrong, modern layouts benefit from Grid for complex two-dimensional arrangements
- **Impact:** Minor; Flexbox works but Grid could provide better layout control

### 11. Hero Section Height Reads as Zero
- The hero section on all pages returns a computed height of 0, suggesting it uses a non-standard element/class for the hero area
- Visually, the hero content displays correctly
- **Impact:** Minor structural concern; no visible user impact

### 12. Lazy-Loaded Images Below Fold Show Placeholder GIFs
- Multiple below-fold images display a 1x1 transparent GIF placeholder
- This suggests JavaScript-based lazy loading that may not trigger for slow connections
- **Impact:** If JS fails, images remain invisible

---

## PAGE-BY-PAGE FINDINGS

### Homepage (ambito.it/)
- **Above the fold (mobile):** H1 "Realizziamo soluzioni e servizi per la Pubblica Amministrazione" is visible. Green highlight bar with value proposition visible. Hero image loads. NO CTA button visible.
- **Above the fold (desktop):** Same as mobile plus navigation bar fully visible. Still no CTA above fold.
- **Layout:** Clean, professional. Two-column layout on desktop correctly stacks to single column on mobile.
- **Cookie banner:** Present on both viewports.

### Chi Siamo (ambito.it/chi-siamo/)
- **Above the fold (mobile):** Shows "Chi siamo" breadcrumb with a subtitle about innovative software. The actual H1 is hidden. No CTA visible.
- **Above the fold (desktop):** Same content with horizontal navigation. "Chi siamo" appears as a styled element but the actual H1 tag is hidden.
- **Layout:** Good text flow. Building image renders well at both sizes.

### Suite Mosaico DigitAI (ambito.it/suite-mosaico-digitai/)
- **Above the fold (mobile):** Mosaico DigitAI logo visible. "La Suite completa per la Pubblica Amministrazione" tagline visible. GREEN CTA "Richiedi una demo gratuita per il tuo Comune" (355x70px) - this is the BEST CTA placement on the entire site.
- **Above the fold (desktop):** Similar but CTA is smaller and less prominent. The CTA "Richiedi una demo gratuita per il tuo Comune" is positioned just at the fold boundary.
- **Layout:** Clean product page. Mobile rendering is actually very good here.

### Contatti (ambito.it/contatti/)
- **Above the fold (mobile):** "Contatti" heading, envelope/phone illustration, and full contact information (address, phone, email, PEC) all visible above fold. No form visible - just static contact details.
- **Above the fold (desktop):** All contact information visible in a single view with office hours below.
- **Issue:** No contact form visible on initial load. Phone number and email are plain text rather than clickable tel: and mailto: links (not verified but typical for text display).

---

## MOBILE RESPONSIVENESS ASSESSMENT

| Criterion | Status | Notes |
|-----------|--------|-------|
| Viewport meta tag | PASS | Correctly set on all pages |
| No horizontal scroll | PASS | No overflow detected on any page |
| Hamburger menu | PASS | Present on all mobile views |
| Touch targets >= 48px | FAIL | Menu 40x40, Search 35x45, breadcrumbs 14px tall |
| Base font >= 16px | FAIL | Body font is 11px - critically undersized |
| Images scale properly | PASS | Images adapt to viewport width |
| Content readable without zoom | FAIL | 11px font requires zooming |
| Flexbox/responsive layout | PASS | 37 flexbox instances, proper stacking |

---

## PRIORITIZED RECOMMENDATIONS

1. **Increase base font size to 16px** (HIGH - affects all pages, all users, and Core Web Vitals)
2. **Add a prominent CTA above the fold on the homepage** such as "Richiedi una demo" or "Scopri le nostre soluzioni" (HIGH - conversion impact)
3. **Fix H1 visibility** on Chi Siamo, Suite Mosaico, and Contatti pages (HIGH - SEO impact)
4. **Change logo loading attribute** from `lazy` to `eager` (MEDIUM - LCP improvement)
5. **Add srcset/sizes** to all images serving multiple sizes (MEDIUM - performance)
6. **Increase touch target sizes** to minimum 48x48px for hamburger, search, and breadcrumbs (MEDIUM - mobile usability)
7. **Add alt text** to certification badge images (LOW - accessibility/SEO)
8. **Enlarge cookie banner dismiss button** to at least 48x48px (LOW - usability)
