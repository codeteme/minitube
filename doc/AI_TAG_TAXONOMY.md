# AI Tag Taxonomy Design

## Why Canonical Tags

For recommendation, retrieval, and analytics, fully free-form tags are noisy and unstable.
This project uses a constrained approach:

1. The model can only choose from an allowed canonical tag list.
2. Stored tags are canonical tags (not arbitrary strings).
3. Optional alias mapping can still absorb wording variation.

This keeps ranking logic simple, deterministic, and easy to debug.

## Current Tables

### `tag_taxonomy`
- `canonical_tag` (PK)
- `display_name`
- `category`
- `active`
- `created_at`

### `tag_aliases`
- `alias` (PK)
- `canonical_tag`
- `created_at`

### `video_tags`
- `video_id` (PK part)
- `tag` (PK part)
- `created_at`

## Current Generation Flow

1. User uploads a video.
2. If user manually selected canonical tags during upload:
   - only canonical tags are accepted
   - AI auto-tagging is skipped for this upload.
3. If user did not select tags:
   - ASR transcript is generated (when enabled)
   - video service triggers dashboard tagging endpoint.
4. Dashboard loads active canonical tags from `tag_taxonomy`.
5. Dashboard calls intelligence `/ai/tagging` with `allowed_tags`.
6. Returned tags are canonicalized via `tag_aliases`.
7. Canonical tags are saved to `video_tags`.

If intelligence is unavailable, dashboard fallback logic still chooses from the same allowed canonical list.

## Frontend Tag Picker

- Canonical options are exposed by `GET /ai/tag-taxonomy` on dashboard service.
- Upload page loads this endpoint and lets users choose from canonical tags only.

## Canonical Tag Set (v1)

The v1 set is intentionally broad, YouTube-like, and not tech-only.

- `general`, `entertainment`, `vlog`, `music`, `gaming`, `sports`
- `news`, `politics`, `education`, `how-to`, `science`, `history`, `documentary`, `technology`
- `business`, `finance`
- `food`, `travel`, `health`, `fitness`, `fashion`, `beauty`, `home`
- `diy`, `automotive`, `pets`, `nature`, `family`, `kids`
- `comedy`, `movies-tv`, `anime`
- `art`, `photography`, `dance`
- `podcast`, `live-stream`, `shorts`

## Recommendation Use (Simple MVP)

Use canonical tags directly in dashboard ranking:

1. Build user profile tags from watch history and likes.
2. Score candidate videos by overlap count with user profile tags.
3. Add a recency bonus and popularity bonus.
4. Filter out already watched videos if desired.

Example score (MVP):

`score = 0.6 * tag_overlap + 0.25 * recency_score + 0.15 * popularity_score`

This avoids calling AI in the online ranking path.

## Governance Rules

- Prefer adding new canonical tags only when repeated demand appears.
- Keep aliases human-friendly and lowercase-hyphen normalized.
- Do not let one alias map to multiple canonical tags.
- Use `active=0` to retire tags without deleting old video tag history.

## Future Extensions

- Add per-tag confidence from intelligence output.
- Support multi-level taxonomy (topic -> subtopic).
- Add user-facing localized display names while keeping canonical IDs stable.
