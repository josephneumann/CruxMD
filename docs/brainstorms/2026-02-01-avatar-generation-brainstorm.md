# Brainstorm: Stylized Avatar Generation Pipeline

**Date**: 2026-02-01
**Status**: Ready for planning

## Problem Statement

CruxMD needs a consistent visual identity for patient and user avatars. Currently, 6 manually-generated watercolor-style avatars exist in `frontend/public/brand/avatars/`. There's no automated pipeline to generate new ones, and images are served from the Next.js public folder (not ideal for generated assets).

## Proposed Solution

Build a Gemini-powered avatar generation service with a consistent watercolor prompt template. Decouple asset serving from the Next.js app by serving static files from a dedicated directory via Caddy.

**Two generation triggers:**
1. **CLI script** — Bulk generate avatars for all seeded patients (run during/after `seed_database.py`)
2. **API endpoint** — `POST /api/patients/{id}/generate-avatar` for on-demand generation (future: accept uploaded profile picture as basis)

## Key Decisions

- **Gemini Imagen 3 via Google AI Studio**: Free tier, good quality image generation. API key in `.env`.
- **VPS + Caddy static dir over Cloudflare R2**: Demo app with <50 patients doesn't need global CDN. Caddy serves `/assets/` from a static directory. Swappable to R2 later by changing base URL.
- **Synchronous generation (no queue)**: 5-15s per image is acceptable. CLI handles bulk, API can be fire-and-forget or return loading state.
- **Moderate image size**: Target ~500KB-1MB per image. Not 8MB originals, not tiny thumbnails.
- **Consistent prompt template**: Watercolor portrait style with CruxMD brand colors. Demographics (name, age, gender) injected into prompt. Physical characteristics inferred by Gemini.

## Prompt Template

```
Generate minimalist, wet-ink watercolor portrait of a {age} y/o {gender} named {name}.
The person is in a neutral, side-profile "observer" pose, facing RIGHT.
The form is defined by soft, bleeding washes of color rather than hard lines.
The primary colors are "Vibrant Forest" (#2F5E52) and "Glacier Teal" (#5A7D7C),
forming the silhouette of the head, {hair_description}, and shoulders.
A subtle, warm wash of "Golden Resin" (#D9A036) is near the eye area, suggesting insight.
The edges of the watercolor are organic and feathery, bleeding into a textured,
off-white "Alabaster" (#F0EAD6) paper background.
No sharp details, just flowing color and texture.
Infer the physical characteristics of the person based on their demographics.
```

## Scope

### In Scope
- `services/avatar_generator.py` — Gemini API wrapper with prompt template
- CLI script for bulk generation (all patients)
- API endpoint for on-demand generation
- Caddy config for `/assets/` static file serving
- Frontend URL migration from `/brand/avatars/` to `/assets/avatars/`
- Image compression/optimization on save
- Config: `GEMINI_API_KEY`, `ASSETS_DIR`, `ASSETS_BASE_URL` env vars

### Out of Scope
- Profile picture upload as generation basis (future — endpoint accepts it, but upload UI not built)
- CDN / Cloudflare R2 migration (revisit when needed)
- Admin UI for regenerating avatars
- Non-avatar image generation

## Open Questions
- Should the CLI script skip patients that already have avatars, or regenerate all?
- What image format? PNG (current) vs WebP (smaller, broad support)?
- Should the API endpoint be authenticated or open?

## Constraints
- Gemini API rate limits (free tier: ~15 RPM for image generation)
- Generation time: 5-15s per image
- VPS disk space (trivial at <50 images)

## Risks
- **Gemini prompt consistency**: Same prompt may produce varying styles across calls. Mitigation: test prompt stability, consider adding seed/style reference.
- **API key management**: New dependency on Google AI Studio. Mitigation: standard `.env` pattern, already used for OpenAI key.
- **Rate limiting during bulk generation**: 50 patients at 15 RPM = ~3-4 min. Mitigation: add delay/retry logic in CLI script.
