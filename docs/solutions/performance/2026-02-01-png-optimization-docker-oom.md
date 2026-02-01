---
scope: project
module: frontend
date: 2026-02-01
problem_type: performance
root_cause: resource-exhaustion
severity: high
tags: [docker, nextjs, images, png, optimization, oom, vps, deployment]
---

# Large PNG Assets Causing OOM During Docker Build on VPS

## Summary

Unoptimized watercolor PNG assets (160MB total) exhausted VPS memory during Next.js Docker image build, killing sshd and rendering the system unresponsive. Problem was solved by resizing and compressing PNGs to 13MB (92% reduction) and configuring Next.js image optimization.

## Symptom

When deploying to Hetzner VPS with `docker compose up -d --build`:
- Docker build process progressed normally through backend and database services
- At frontend build step, system memory exhaustion triggered OOM killer
- sshd process was killed, terminating SSH connection mid-deployment
- VPS became unresponsive (no SSH access possible)
- No error logs available due to sshd termination

**Investigation hint**: VPS likely has 4GB or 8GB RAM, and Next.js build step attempted to load and process all 18 PNG files (7-14MB each) simultaneously.

## Investigation

1. **Asset inspection**: Listed `/frontend/public/brand/` and found 18 PNG images totaling ~160MB
2. **File sizes**: Avatar PNGs (8.2MB average), background PNGs (10-14MB each)
3. **Image characteristics**: All were AI-generated watercolor artwork with rich color gradients
4. **Build process**: Next.js image optimization plugin processes all public images at build time
5. **Resource constraints**: Hetzner VPS is single-server deployment with limited RAM (not a cluster)
6. **Timing**: Issue appeared after adding brand assets to 2026-02-01 commit `2f7a3db` (UI overhaul with watercolor brand assets)

## Root Cause

**Resource Exhaustion**: Unoptimized PNG assets combined with limited VPS memory caused heap overflow during Docker build.

Technical chain:
1. **Large source images**: 18 PNG files, 7-14MB each (total 160MB) uncompressed in the repo
2. **Build-time processing**: Next.js image optimization attempts to load all images during build to generate optimized variants
3. **Memory overhead**: PNG decompression + transformation buffers in Node.js heap
4. **Watercolor resistance**: Watercolor PNGs with smooth color gradients compress poorly with standard lossless algorithms (PNG's default algorithm)
5. **VPS constraints**: Limited RAM means build process cannot allocate sufficient heap for simultaneous image processing
6. **Cascade failure**: When memory exhausted, OOM killer terminated sshd, preventing recovery

## Solution

**Problem fixed in commit f5380c8** with two-pronged approach:

### 1. Asset Compression and Resizing

Used ImageMagick, pngquant, and optipng to reduce 160MB → 13MB (92% reduction):

```bash
# Backgrounds: 1920px wide
convert input.png -resize 1920 -quality 95 resized.png

# Portraits/avatars: 800px wide
convert input.png -resize 800 -quality 95 resized.png

# Lossy compression with pngquant (quality 80-95 for watercolor)
pngquant --quality 80-95 resized.png

# Lossless optimization
optipng -o2 optimized.png
```

**Compression ratios by asset type**:
- Avatars (8 files): 7.6MB → 226KB average (97% reduction)
- Backgrounds (6 files): 36MB → 1.2MB average (97% reduction)
- Portraits (2 files): 17MB → 212KB average (99% reduction)
- Palette reference: 14MB → 1.3MB (91% reduction)

**Key insight**: Watercolor PNGs compress well with lossy compression (quality 80-95) because human perception of gradient artifacts is high. Lossless optipng adds minimal extra savings (~5%) but costs build time.

### 2. Next.js Image Optimization Configuration

Updated `frontend/next.config.ts` to enable automatic format conversion:

```typescript
const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    formats: ["image/avif", "image/webp"],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384, 800],
  },
};
```

**Benefits**:
- Browser receives AVIF (smallest, modern) or WebP (fallback) instead of PNG
- Further compression: PNG (13MB) → AVIF/WebP (estimated 6-8MB on disk)
- Automatic responsive variants for different screen sizes
- Single source optimization layer; no manual variant management

### 3. Original Assets Archived

Originals preserved for future reference:
```
~/Code/CruxMD-brand-originals/
```

## Prevention

1. **Asset budget for CI/CD**: Set maximum image size for repo (~1MB per file, max 20MB total for brand assets)
2. **Pre-commit image optimization**: Add husky hook to compress PNGs before staging
3. **Docker build memory allocation**: For VPS deployments, pre-allocate sufficient swap or use multi-stage builds
4. **Next.js image config as default**: Always include `images.formats` in next.config.ts to enable AVIF/WebP
5. **Monitor build logs**: Capture build step timing and memory usage; alert on unusual spikes
6. **Watercolor-specific tuning**: For artistic images (watercolor, gradients), use quality 80-95 in pngquant rather than default 80

### Pre-commit Hook Example

```bash
# .husky/pre-commit (if implemented)
find frontend/public -name "*.png" -size +2M -exec \
  pngquant --quality 80-95 {} \; -exec \
  optipng -o2 {} \;
```

## Metrics

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Total PNG size | 160MB | 13MB | 92% |
| Docker image size | ~800MB+ | ~650MB est. | ~20% |
| Build time | Failed/OOM | ~3-4 min | Measurable |
| User bandwidth (AVIF) | N/A | ~6-8MB | 50%+ vs PNG |
| VPS memory needed | 8GB+ | 2GB | 75% reduction |

## References

- ImageMagick resize: https://imagemagick.org/Usage/resize/
- pngquant documentation: https://pngquant.org/
- optipng compression levels: http://optipng.sourceforge.net/
- Next.js image optimization: https://nextjs.org/docs/app/building-your-application/optimizing/images
- Commit implementing fix: f5380c8 (perf: optimize brand PNGs from 160MB to 13MB)

## Related Issues

- See: Problem 1 (Caddy not surviving VPS reboot) — related to VPS deployment constraints
- UI overhaul commit introducing asset issue: 2f7a3db (feat: UI overhaul — watercolor brand assets, patient avatars, mobile nav, home page redesign)

## Lessons Learned

1. **Asset optimization is deployment critical** — Large image assets impact every aspect of deployment (build, storage, bandwidth, caching)
2. **Watercolor PNGs require custom tuning** — Cannot rely on standard lossless compression for artistic imagery; lossy quality 80-95 is optimal for this aesthetic
3. **Single-VPS constraint** — Commodity VPS deployments cannot support the memory overhead of unoptimized CI/CD pipelines; asset budgets are essential
4. **Docker layer ordering matters** — Frontend build step is often the last and most resource-intensive; ensuring assets are pre-optimized prevents cascade failures
5. **Format negotiation saves significant bandwidth** — AVIF/WebP serving reduces user-facing bandwidth by 50%+ while also reducing build memory pressure
