---
title: "feat: Avatar Generation Pipeline"
type: feat
date: 2026-02-01
brainstorm: docs/brainstorms/2026-02-01-avatar-generation-brainstorm.md
---

# feat: Avatar Generation Pipeline

## Overview

Build an automated avatar generation pipeline using Google Gemini (Imagen 3 / gemini-2.5-flash-image) to create consistent watercolor-style patient portraits. Decouple asset serving from the Next.js app by serving generated images from a Caddy static directory.

## Problem Statement

CruxMD needs a consistent visual identity for patient avatars. Currently 6 manually-generated watercolor avatars exist in `frontend/public/brand/avatars/`. No automated pipeline, no scalable serving strategy.

## Proposed Solution

Three components:

1. **Backend service** (`services/avatar_generator.py`) — wraps Gemini API with a consistent prompt template, handles image saving and compression
2. **CLI script** (`scripts/generate_avatars.py`) — bulk generation for all seeded patients
3. **API endpoint** (`POST /api/avatars/generate/{patient_id}`) — on-demand generation

Plus infrastructure changes: Caddy static dir for `/assets/`, Docker volume mount, frontend URL migration.

## Technical Approach

### Model Choice

Use `google-genai` SDK with **`imagen-3.0-generate-002`** via `generate_images()` for dedicated image generation. Falls back to `gemini-2.5-flash-image` if Imagen is unavailable on the free tier.

Key config:
- `person_generation="ALLOW_ADULT"` (required for portraits)
- `output_mime_type="image/png"`
- `aspect_ratio="1:1"` (square avatars)
- `number_of_images=1`

### Slug / File Naming

**Use patient FHIR ID** as the file identifier, not patient name. Reasons:
- Synthea can produce duplicate names
- FHIR ID is guaranteed unique
- Frontend lookup changes from name-slug to ID-based

File pattern: `/assets/avatars/{fhir_id}.png`

Frontend change in `PatientSummaryCard.tsx`:
```typescript
// Before
const avatarSlug = name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/\s+/g, "-");
const avatarSrc = `/brand/avatars/${avatarSlug}.png`;

// After
const avatarSrc = `/assets/avatars/${patient.fhir_id}.png`;
```

### Prompt Template

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

Demographics extracted from FHIR Patient resource:
- `name` — cleaned (strip Synthea suffixes via existing `fhir_loader.py` logic)
- `gender` — from `Patient.gender`
- `age` — calculated from `Patient.birthDate`
- `hair_description` — inferred from age/gender (e.g., "gray hair" for 80+, "brown hair" default)

### Asset Serving Architecture

```
                    ┌──────────┐
  Browser ──────────▶  Caddy   │
                    │          │
  /assets/*  ───────▶ file_server /data/assets/
  /api/*     ───────▶ reverse_proxy backend:8000
  /*         ───────▶ reverse_proxy frontend:3000
                    └──────────┘

  Docker volumes:
    ./assets:/data/assets  (shared between backend + caddy)
```

Caddy config addition:
```
handle /assets/* {
    root * /data/assets
    file_server
    header Cache-Control "public, max-age=86400"
}
```

Docker compose changes:
```yaml
backend:
  volumes:
    - ./assets:/data/assets

caddy:
  volumes:
    - ./assets:/data/assets:ro
```

### Regeneration Policy

- **CLI default**: Skip patients that already have an avatar file on disk
- **CLI `--force` flag**: Regenerate all, overwriting existing
- **API endpoint**: Always regenerates (explicit action = intentional)
- **Rationale**: Non-deterministic outputs mean regeneration changes the face. Skip-by-default preserves visual consistency.

### Error Handling

| Scenario | CLI Behavior | API Behavior |
|---|---|---|
| Content filter rejection | Log warning, skip patient | Return 422 with reason |
| Rate limit (429) | Exponential backoff, max 3 retries | Return 429 to caller |
| Gemini API down | Abort batch with summary | Return 503 |
| Missing demographics | Use defaults (unknown gender → "person") | Same |
| Disk write failure | Abort batch | Return 500 |

### Authentication

API endpoint uses existing `Depends(verify_bearer_token)` pattern — same as all other routes.

## Acceptance Criteria

- [ ] `AvatarGeneratorService` in `backend/app/services/avatar_generator.py` wraps Gemini API with prompt template
- [ ] `GEMINI_API_KEY` added to `backend/app/config.py` Settings
- [ ] CLI script `backend/app/scripts/generate_avatars.py` generates avatars for all patients
- [ ] CLI supports `--force` flag for regeneration and `--dry-run` for testing
- [ ] API endpoint `POST /api/avatars/generate/{patient_id}` generates on-demand
- [ ] Caddy serves `/assets/*` from static directory with cache headers
- [ ] Docker compose mounts `./assets` volume for backend and caddy
- [ ] Frontend `PatientSummaryCard` uses FHIR ID for avatar URL, served from `/assets/avatars/`
- [ ] Existing manually-generated avatars migrated to new location with FHIR ID filenames
- [ ] Rate limiting with exponential backoff in CLI script
- [ ] Content filter failures logged and handled gracefully
- [ ] `google-genai` added to backend dependencies via `uv add`

## Dependencies & Risks

**Dependencies:**
- Google AI Studio API key (user needs to create account)
- `google-genai` Python package

**Risks:**
- **Content filter rejections**: Gemini may reject prompts with demographic details. Mitigation: test with actual Synthea patients, soften prompt if needed.
- **No seed/reproducibility**: Each generation produces a different image. Mitigation: skip-by-default policy preserves consistency.
- **Rate limits on free tier**: ~15 RPM (flash) or ~2 RPM (imagen). Mitigation: backoff + retry in CLI, accept generation time for bulk.
- **Imagen 3 availability**: May not be available on free tier. Mitigation: fall back to gemini-2.5-flash-image.

## Implementation Phases

### Phase 1: Infrastructure (no API calls)
- Add `GEMINI_API_KEY` to config
- Add `google-genai` dependency
- Set up `./assets` directory + Docker volume mounts
- Add Caddy `/assets/*` static file serving
- Migrate existing avatars to new location

### Phase 2: Core Service
- Implement `AvatarGeneratorService` with prompt template
- Implement demographic extraction from FHIR Patient
- Image saving with compression

### Phase 3: CLI Script
- Implement `generate_avatars.py` with skip/force/dry-run
- Rate limiting and retry logic
- Progress reporting

### Phase 4: API Endpoint
- `POST /api/avatars/generate/{patient_id}` route
- Auth via bearer token
- Error handling (422, 429, 503)

### Phase 5: Frontend Migration
- Update `PatientSummaryCard` avatar URL to use FHIR ID + `/assets/` path
- Update `Sidebar` admin avatar path
- Remove old avatar files from `frontend/public/brand/avatars/`

## References

- Brainstorm: `docs/brainstorms/2026-02-01-avatar-generation-brainstorm.md`
- Existing avatar usage: `frontend/components/patient/PatientSummaryCard.tsx:30-48`
- Service pattern: `backend/app/services/embeddings.py:414-450`
- CLI pattern: `backend/app/scripts/seed_database.py:123-152`
- Route pattern: `backend/app/routes/patients.py:19-102`
- Config pattern: `backend/app/config.py:18-76`
- FHIR patient data: `fixtures/synthea/patient_bundle_1.json`
- Caddy config: `Caddyfile:1-66`
- Docker compose: `docker-compose.yml:1-80`
- [Google Gemini Imagen API docs](https://ai.google.dev/gemini-api/docs/imagen)
- [google-genai Python SDK](https://github.com/googleapis/python-genai)
