# CruxMD Brand Assets Specification

> A complete inventory of required brand assets for the CruxMD web application

---

## Overview

This document specifies all brand assets needed for a modern web application, including logo system variations, favicons, PWA icons, social sharing images, and usage guidelines. Based on 2025 best practices.

**Priority Levels:**
- **P0 (Critical)**: Must have for launch. Site looks broken without these.
- **P1 (Recommended)**: Should have. Improves user experience and brand consistency.
- **P2 (Nice-to-Have)**: Can add later. Covers edge cases and premium polish.

---

## 1. Logo System

A comprehensive brand identity requires multiple logo variations that work across different contexts, sizes, and backgrounds.

### Logo Types Explained

| Type | Description | When to Use |
|------|-------------|-------------|
| **Primary Logo (Combination Mark)** | Full logo with wordmark + mark together | Headers, marketing, large formats |
| **Wordmark (Logotype)** | Text-only logo spelling "CruxMD" | When horizontal space is available, formal contexts |
| **Logomark (Symbol)** | Icon/symbol only (no text) | Favicons, app icons, small spaces, watermarks |
| **Submark** | Simplified secondary mark | Social avatars, stamps, compact spaces |
| **Lockup** | Logo + tagline or descriptor | Marketing materials, landing pages |

### 1.1 Primary Logo (Combination Mark) — P0

The main logo combining the mark and wordmark. Use this as the default wherever space permits.

| File | Color | Background | Format | Use Case |
|------|-------|------------|--------|----------|
| `logo-primary.svg` | Book Cloth `#CC785C` | Transparent | SVG | Web, marketing, large formats |
| `logo-primary.png` | Book Cloth `#CC785C` | Transparent | PNG | Fallback when SVG unsupported |
| `logo-primary@2x.png` | Book Cloth `#CC785C` | Transparent | PNG | Retina displays (2x) |
| `logo-primary@3x.png` | Book Cloth `#CC785C` | Transparent | PNG | High-DPI displays (3x) |

### 1.2 Wordmark Only — P1

Text-based logo for contexts where the full combination mark is too complex.

| File | Color | Use Case |
|------|-------|----------|
| `wordmark-primary.svg` | Book Cloth `#CC785C` | Headers, horizontal layouts |
| `wordmark-reversed.svg` | Ivory Light `#FAFAF7` | Dark backgrounds |
| `wordmark-mono-dark.svg` | Slate Dark `#191919` | Single-color print |
| `wordmark-mono-light.svg` | White `#FFFFFF` | Reversed single-color |

### 1.3 Logomark (Symbol/Icon) — P0

Simplified mark for favicons, app icons, and small spaces. Should be recognizable at 16x16 pixels.

| File | Color | Use Case |
|------|-------|----------|
| `mark-primary.svg` | Book Cloth `#CC785C` | Favicons, app icons, watermarks |
| `mark-reversed.svg` | Ivory Light `#FAFAF7` | Dark backgrounds, dark mode |
| `mark-mono.svg` | Slate Dark `#191919` | Single-color applications |
| `mark-mono-light.svg` | White `#FFFFFF` | Reversed single-color |

**Design Requirements for Logomark:**
- Must be legible at 16x16 pixels
- Single focal point (avoid fine details)
- Works on both light and dark backgrounds
- High contrast for visibility in browser tabs

### 1.4 Reversed Variants (Dark Backgrounds) — P0

| File | Color | Use Case |
|------|-------|----------|
| `logo-reversed.svg` | Ivory Light `#FAFAF7` | Dark headers, dark mode |
| `logo-reversed.png` | Ivory Light `#FAFAF7` | PNG fallback |

### 1.5 Monochrome Variants — P1

For single-color contexts: print, embroidery, co-branding, or when color isn't available.

| File | Color | Use Case |
|------|-------|----------|
| `logo-mono-dark.svg` | Slate Dark `#191919` | Print, embroidery, fax |
| `logo-mono-light.svg` | White `#FFFFFF` | Reversed single-color |

### 1.6 Submark — P1

A compact, simplified version for very small applications (social avatars, stamps).

| File | Color | Use Case |
|------|-------|----------|
| `submark-primary.svg` | Book Cloth `#CC785C` | Social profile pictures, stamps |
| `submark-reversed.svg` | Ivory Light `#FAFAF7` | Dark backgrounds |

### 1.7 Logo with Tagline (Lockup) — P2

Full logo paired with tagline for marketing contexts.

| File | Tagline | Use Case |
|------|---------|----------|
| `logo-tagline.svg` | "Clinical Intelligence" | Marketing, landing pages |
| `logo-tagline-reversed.svg` | "Clinical Intelligence" | Dark backgrounds |

---

## 2. Logo Usage Rules

### Clear Space

The logo must have breathing room. Define clear space using the height of the "C" in CruxMD as the unit (marked as `X`).

```
Minimum clear space: 0.5X on all sides
Recommended: 1X on all sides for marketing materials
```

**Visual:**
```
    ┌─────────────────────────┐
    │         0.5X            │
    │   ┌───────────────┐     │
    │0.5X│   CruxMD    │0.5X  │
    │   └───────────────┘     │
    │         0.5X            │
    └─────────────────────────┘
```

### Minimum Sizes

Below these sizes, the logo becomes illegible. Use the logomark instead.

| Logo Type | Print (mm) | Digital (px) |
|-----------|------------|--------------|
| Primary Logo | 25mm wide | 120px wide |
| Wordmark | 20mm wide | 100px wide |
| Logomark | 5mm | 16px |

### What NOT to Do

- ❌ Stretch, squeeze, or distort proportions
- ❌ Rotate the logo
- ❌ Add drop shadows, bevels, or effects
- ❌ Change the colors outside approved palette
- ❌ Place on busy backgrounds without contrast
- ❌ Separate or rearrange logo elements
- ❌ Add outlines or strokes
- ❌ Use low-resolution versions when vectors available

---

## 3. Favicon Set

Favicons appear in browser tabs, bookmarks, and search results. Modern best practice: **SVG + minimal PNG fallbacks**.

### Modern Minimal Approach (Recommended) — P0

In 2025, you only need 3-4 files to cover 99% of use cases:

| File | Size | Format | Purpose | Priority |
|------|------|--------|---------|----------|
| `favicon.svg` | Scalable | SVG | Modern browsers (Chrome 80+, Firefox 72+, Edge 80+) | P0 |
| `favicon.ico` | 32x32 | ICO | Legacy browsers, Google Search | P0 |
| `favicon-48x48.png` | 48x48 | PNG | Google Search results (minimum required) | P0 |
| `apple-touch-icon.png` | 180x180 | PNG | iOS "Add to Home Screen" | P0 |

**Why SVG First:**
- Single file scales to any size
- Smaller file size than multiple PNGs
- Supports dark mode via CSS `prefers-color-scheme`
- Future-proof

**SVG Dark Mode Support:**
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <style>
    .icon { fill: #CC785C; }
    @media (prefers-color-scheme: dark) {
      .icon { fill: #FAFAF7; }
    }
  </style>
  <path class="icon" d="..."/>
</svg>
```

### Extended Favicon Sizes — P1

For maximum compatibility and polish:

| File | Size | Purpose |
|------|------|---------|
| `favicon-16x16.png` | 16x16 | Browser tabs (standard DPI) |
| `favicon-32x32.png` | 32x32 | Browser tabs (Retina/HiDPI) |
| `favicon-48x48.png` | 48x48 | Windows taskbar, Google Search |
| `favicon-64x64.png` | 64x64 | macOS Dock |
| `favicon-96x96.png` | 96x96 | Google recommendations |

### P2 — Additional Sizes (Edge Cases)

| File | Size | Purpose |
|------|------|---------|
| `favicon-128x128.png` | 128x128 | Chrome Web Store |
| `favicon-256x256.png` | 256x256 | Windows high-res |

### Favicon Design Guidelines

1. **Simplicity wins**: At 16px, details become noise. Use a single icon or letter.
2. **Test dark mode**: Your favicon must be visible on light AND dark browser tabs.
3. **High contrast**: Avoid light colors on light backgrounds.
4. **No text**: Wordmarks are illegible at favicon sizes—use the logomark.
5. **Design at 64x64**: Then scale down to test legibility at 16x16.

---

## 4. Apple Touch Icons

Required for iOS/iPadOS "Add to Home Screen" functionality.

### Required — P0

| File | Size | Device |
|------|------|--------|
| `apple-touch-icon.png` | 180x180 | iPhone (all modern devices) |

### Recommended — P1

| File | Size | Device |
|------|------|--------|
| `apple-touch-icon-152x152.png` | 152x152 | iPad, iPad Mini |
| `apple-touch-icon-167x167.png` | 167x167 | iPad Pro |
| `apple-touch-icon-120x120.png` | 120x120 | iPhone (older models) |

### Apple Touch Icon Requirements

| Requirement | Details |
|-------------|---------|
| **No transparency** | Must have solid, opaque background. iOS adds black background to transparent icons. |
| **No rounded corners** | iOS applies rounded corners automatically. Square corners in source file. |
| **Background color** | Use Ivory Light `#FAFAF7` or Book Cloth `#CC785C` as background. |
| **Safe zone** | Keep logo content within center 80% to avoid edge clipping. |
| **File format** | PNG only (JPEG works but PNG preferred). |

### Safari Pinned Tab (Mask Icon) — P1

For Safari's pinned tabs feature on macOS. Must be monochrome SVG.

| File | Format | Color Attribute |
|------|--------|-----------------|
| `safari-pinned-tab.svg` | SVG (monochrome) | `color="#CC785C"` |

**Requirements:**
- SVG format only
- Single color: 100% black (`#000000`) vectors
- Transparent background (no background)
- Square aspect ratio
- Safari applies the `color` attribute when tab is active

---

## 5. PWA / Web App Manifest Icons

Required for Progressive Web App installation on mobile and desktop.

### Minimum Required (PWA Installability) — P0

Without these, Chromium browsers won't allow PWA installation:

| File | Size | Purpose |
|------|------|---------|
| `pwa-192x192.png` | 192x192 | Home screen icon, Chrome/Edge installation |
| `pwa-512x512.png` | 512x512 | Splash screen, high-res displays |
| `pwa-maskable-512x512.png` | 512x512 | Adaptive icon (masked by OS) |

### Recommended Full Set — P1

| File | Size | Purpose |
|------|------|---------|
| `pwa-72x72.png` | 72x72 | Legacy Android |
| `pwa-96x96.png` | 96x96 | Android 3x density |
| `pwa-128x128.png` | 128x128 | Chrome Web Store |
| `pwa-144x144.png` | 144x144 | Android 3x density |
| `pwa-192x192.png` | 192x192 | Android 4x density |
| `pwa-256x256.png` | 256x256 | High-res displays |
| `pwa-384x384.png` | 384x384 | Microsoft Edge |
| `pwa-512x512.png` | 512x512 | Splash screens |

### Maskable Icons (Adaptive Icon Support) — P0

Maskable icons allow the OS to apply shape masks (circle, squircle, rounded square) without clipping important content.

| File | Size | Safe Zone |
|------|------|-----------|
| `pwa-maskable-192x192.png` | 192x192 | 80% center (154x154 content area) |
| `pwa-maskable-512x512.png` | 512x512 | 80% center (410x410 content area) |

### Maskable Icon Safe Zone

```
┌─────────────────────────────┐
│      10% margin (unsafe)    │
│   ┌─────────────────────┐   │
│   │                     │   │
│   │   80% SAFE ZONE     │   │
│   │   (keep logo here)  │   │
│   │                     │   │
│   └─────────────────────┘   │
│      10% margin (unsafe)    │
└─────────────────────────────┘
```

**For 512x512 maskable icon:**
- Total canvas: 512x512px
- Safe zone: 410x410px (centered)
- Margin: 51px on each side (may be cropped)

**Important:** Do NOT use `"purpose": "any maskable"` — this is deprecated and causes padding issues. Create separate icons:
- Standard icons: `"purpose": "any"` (default, no need to specify)
- Maskable icons: `"purpose": "maskable"`

### Testing Tools

- [Maskable.app](https://maskable.app/) — Preview how maskable icons appear with different masks

---

## 6. Social Media / Open Graph Images

For link previews when sharing on social platforms. Optimized OG images can increase click-through rates by 40-50%.

### Universal OG Image — P0

| File | Size | Aspect Ratio | Platforms |
|------|------|--------------|-----------|
| `og-image.png` | 1200x630 | 1.91:1 | Facebook, LinkedIn, Discord, Slack, iMessage |

### Platform-Specific — P1

| File | Size | Aspect Ratio | Platform |
|------|------|--------------|----------|
| `og-image-twitter.png` | 1200x675 | 16:9 | Twitter/X (summary_large_image cards) |
| `og-image-square.png` | 1200x1200 | 1:1 | LinkedIn (optional, performs well) |

### Design Guidelines

| Guideline | Details |
|-----------|---------|
| **Safe zone** | Keep critical content in center 80% (platforms crop edges) |
| **Include logo** | Brand visibility in link previews |
| **Minimal text** | Large, readable at thumbnail size (150-300px wide) |
| **Brand colors** | Use Book Cloth `#CC785C` and Ivory Light `#FAFAF7` |
| **File size** | Under 1MB (ideally 100-300KB). Max 5MB for Facebook. |
| **File format** | PNG for graphics/text, JPEG for photos |
| **No transparency** | Social platforms don't support transparent OG images |

### Minimum Requirements (per platform)

| Platform | Minimum Size | Maximum Size | Notes |
|----------|--------------|--------------|-------|
| Facebook | 600x315 | 8MB | 1200x630 recommended |
| Twitter/X | 800x418 | 5MB | 1200x675 for large cards |
| LinkedIn | 1200x627 | 5MB | Square (1:1) also works well |
| Discord | 1200x630 | — | Uses og:image |
| Slack | 1200x630 | — | Uses og:image |

### Testing Tools

- [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/)
- [Twitter Card Validator](https://cards-dev.twitter.com/validator)
- [LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/)
- [OpenGraph.xyz](https://www.opengraph.xyz/) — Universal preview tool

---

## 7. Color Reference

| Name | Hex | RGB | HSL | Usage |
|------|-----|-----|-----|-------|
| **Book Cloth** | `#CC785C` | 204, 120, 92 | 15°, 50%, 58% | Primary brand, CTAs |
| **Ivory Light** | `#FAFAF7` | 250, 250, 247 | 60°, 23%, 97% | Light backgrounds |
| **Slate Dark** | `#191919` | 25, 25, 25 | 0°, 0%, 10% | Text, dark mono |
| **White** | `#FFFFFF` | 255, 255, 255 | 0°, 0%, 100% | Reversed mono |
| **Sage** | `#7D8B6F` | 125, 139, 111 | 90°, 11%, 49% | Accent (success, health) |
| **Periwinkle** | `#8B8FC7` | 139, 143, 199 | 236°, 33%, 66% | Accent (info, links) |

### Color Accessibility

| Combination | Contrast Ratio | WCAG Level |
|-------------|----------------|------------|
| Book Cloth on Ivory Light | 3.2:1 | AA Large Text |
| Slate Dark on Ivory Light | 16.5:1 | AAA |
| Ivory Light on Slate Dark | 16.5:1 | AAA |
| Book Cloth on Slate Dark | 5.1:1 | AA |

---

## 8. HTML Implementation

### Head Tags — Minimal (P0)

Covers 99% of use cases with just 5 lines:

```html
<!-- Favicon (SVG + ICO fallback) -->
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="32x32">

<!-- Apple Touch Icon -->
<link rel="apple-touch-icon" href="/apple-touch-icon.png">

<!-- Web App Manifest -->
<link rel="manifest" href="/manifest.webmanifest">

<!-- Theme Color -->
<meta name="theme-color" content="#CC785C">
```

### Head Tags — Comprehensive (P1)

For maximum compatibility:

```html
<!-- Favicons -->
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48x48.png">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">

<!-- Apple Touch Icons -->
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="apple-touch-icon" sizes="167x167" href="/apple-touch-icon-167x167.png">
<link rel="apple-touch-icon" sizes="152x152" href="/apple-touch-icon-152x152.png">

<!-- Safari Pinned Tab -->
<link rel="mask-icon" href="/safari-pinned-tab.svg" color="#CC785C">

<!-- Web App Manifest -->
<link rel="manifest" href="/manifest.webmanifest">

<!-- Theme Colors (light/dark mode) -->
<meta name="theme-color" content="#CC785C" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#191919" media="(prefers-color-scheme: dark)">

<!-- Open Graph -->
<meta property="og:type" content="website">
<meta property="og:image" content="https://cruxmd.ai/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="CruxMD - Clinical Intelligence">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://cruxmd.ai/og-image-twitter.png">
<meta name="twitter:image:alt" content="CruxMD - Clinical Intelligence">
```

### manifest.webmanifest

```json
{
  "name": "CruxMD",
  "short_name": "CruxMD",
  "description": "Clinical intelligence for physicians",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#FAFAF7",
  "theme_color": "#CC785C",
  "icons": [
    {
      "src": "/pwa-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/pwa-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    },
    {
      "src": "/pwa-maskable-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "maskable"
    },
    {
      "src": "/pwa-maskable-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }
  ]
}
```

**Extended manifest (P1)** — Add these icons for broader device support:

```json
{
  "icons": [
    { "src": "/pwa-72x72.png", "sizes": "72x72", "type": "image/png" },
    { "src": "/pwa-96x96.png", "sizes": "96x96", "type": "image/png" },
    { "src": "/pwa-128x128.png", "sizes": "128x128", "type": "image/png" },
    { "src": "/pwa-144x144.png", "sizes": "144x144", "type": "image/png" },
    { "src": "/pwa-192x192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/pwa-256x256.png", "sizes": "256x256", "type": "image/png" },
    { "src": "/pwa-384x384.png", "sizes": "384x384", "type": "image/png" },
    { "src": "/pwa-512x512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/pwa-maskable-192x192.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable" },
    { "src": "/pwa-maskable-512x512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

---

## 9. File Organization

Recommended directory structure:

```
public/
├── favicon.ico                    # P0: Legacy browsers
├── favicon.svg                    # P0: Modern browsers (with dark mode)
├── favicon-16x16.png              # P1: Browser tabs
├── favicon-32x32.png              # P1: Retina browser tabs
├── favicon-48x48.png              # P0: Google Search
├── apple-touch-icon.png           # P0: iOS home screen (180x180)
├── apple-touch-icon-152x152.png   # P1: iPad
├── apple-touch-icon-167x167.png   # P1: iPad Pro
├── safari-pinned-tab.svg          # P1: Safari pinned tabs
├── manifest.webmanifest           # P0: PWA manifest
├── og-image.png                   # P0: Social sharing (1200x630)
├── og-image-twitter.png           # P1: Twitter cards (1200x675)
├── pwa-192x192.png                # P0: PWA icon
├── pwa-512x512.png                # P0: PWA splash
├── pwa-maskable-192x192.png       # P0: Adaptive icon
├── pwa-maskable-512x512.png       # P0: Adaptive splash
├── pwa-72x72.png                  # P1: Legacy Android
├── pwa-96x96.png                  # P1: Android 3x
├── pwa-128x128.png                # P1: Chrome Web Store
├── pwa-144x144.png                # P1: Android 3x
├── pwa-256x256.png                # P1: High-res
├── pwa-384x384.png                # P1: Microsoft Edge
│
└── brand/
    ├── logo-primary.svg           # P0: Main logo (vector)
    ├── logo-primary.png           # P0: Main logo (raster)
    ├── logo-primary@2x.png        # P1: Retina
    ├── logo-primary@3x.png        # P2: High-DPI
    ├── logo-reversed.svg          # P0: Dark backgrounds
    ├── logo-reversed.png          # P1: Dark backgrounds (raster)
    ├── logo-mono-dark.svg         # P1: Single-color dark
    ├── logo-mono-light.svg        # P1: Single-color light
    ├── wordmark-primary.svg       # P1: Text-only logo
    ├── wordmark-reversed.svg      # P1: Text-only reversed
    ├── mark-primary.svg           # P0: Icon/symbol (used for favicons)
    ├── mark-reversed.svg          # P0: Icon/symbol reversed
    ├── mark-mono.svg              # P1: Icon/symbol mono
    ├── submark-primary.svg        # P1: Compact mark
    ├── logo-tagline.svg           # P2: Logo with tagline
    └── brand-guidelines.pdf       # P2: Full brand guidelines doc
```

---

## 10. Complete Asset Checklist

### P0 — Critical (Launch Blockers)

**Favicons:**
- [ ] `favicon.svg` (with dark mode CSS)
- [ ] `favicon.ico` (32x32)
- [ ] `favicon-48x48.png`

**Apple:**
- [ ] `apple-touch-icon.png` (180x180, solid background)

**PWA:**
- [ ] `pwa-192x192.png`
- [ ] `pwa-512x512.png`
- [ ] `pwa-maskable-512x512.png` (with safe zone)

**Social:**
- [ ] `og-image.png` (1200x630)

**Logo:**
- [ ] `logo-primary.svg`
- [ ] `logo-primary.png`
- [ ] `logo-reversed.svg`
- [ ] `mark-primary.svg` (for favicons)
- [ ] `mark-reversed.svg`

**Config:**
- [ ] `manifest.webmanifest`
- [ ] HTML head tags (minimal set)

### P1 — Recommended (Launch Ready)

**Favicons:**
- [ ] `favicon-16x16.png`
- [ ] `favicon-32x32.png`

**Apple:**
- [ ] `apple-touch-icon-152x152.png`
- [ ] `apple-touch-icon-167x167.png`
- [ ] `safari-pinned-tab.svg`

**PWA:**
- [ ] `pwa-maskable-192x192.png`
- [ ] Additional sizes (72, 96, 128, 144, 256, 384)

**Social:**
- [ ] `og-image-twitter.png` (1200x675)

**Logo:**
- [ ] `logo-primary@2x.png`
- [ ] `logo-reversed.png`
- [ ] `logo-mono-dark.svg`
- [ ] `logo-mono-light.svg`
- [ ] `wordmark-primary.svg`
- [ ] `wordmark-reversed.svg`
- [ ] `submark-primary.svg`
- [ ] `mark-mono.svg`

### P2 — Nice-to-Have (Polish)

**Favicons:**
- [ ] `favicon-64x64.png`
- [ ] `favicon-96x96.png`
- [ ] `favicon-128x128.png`
- [ ] `favicon-256x256.png`

**Social:**
- [ ] `og-image-square.png` (1200x1200)

**Logo:**
- [ ] `logo-primary@3x.png`
- [ ] `logo-tagline.svg`
- [ ] `wordmark-mono-dark.svg`
- [ ] `wordmark-mono-light.svg`

**Documentation:**
- [ ] `brand-guidelines.pdf`

---

## 11. Generation Tools

### Recommended Workflow

1. **Create master assets in Figma:**
   - Logo at high resolution (1024px+ width)
   - Logomark at 512x512 with proper safe zones

2. **Export SVGs** directly from Figma for vector assets

3. **Use a generator for icon sets:**
   - [RealFaviconGenerator.net](https://realfavicongenerator.net/) — Comprehensive, handles all edge cases
   - [Favicon.io](https://favicon.io/) — Simple, fast
   - [Maskable.app](https://maskable.app/editor) — Maskable icon editor

4. **Validate:**
   - [Google Lighthouse](https://developers.google.com/web/tools/lighthouse) — PWA audit
   - [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/) — OG image validation
   - Browser DevTools → Application → Manifest — PWA icon validation

---

## Sources

- [Evil Martians: How to Favicon in 2025](https://evilmartians.com/chronicles/how-to-favicon-in-2021-six-files-that-fit-most-needs)
- [Webflow: Favicons Guide](https://webflow.com/blog/favicon-guide)
- [Figma: Types of Logos](https://www.figma.com/resource-library/types-of-logos/)
- [MDN: Define PWA App Icons](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/How_to/Define_app_icons)
- [Chrome Developers: Maskable Icon Audit](https://developer.chrome.com/docs/lighthouse/pwa/maskable-icon-audit)
- [Apple: Safari Pinned Tabs](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/pinnedTabs/pinnedTabs.html)
- [OG Image Gallery: Dimensions Guide](https://www.ogimage.gallery/libary/the-ultimate-guide-to-og-image-dimensions-2024-update)

---

*Specification updated: January 2025*
*Based on 2025 web standards and best practices*
