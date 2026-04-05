# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## What this is

Runeform POC 3 — a compositional layout engine for brand marketing. This proof of concept demonstrates three architectural concepts:

1. **Z3 typography constraint solving** — font sizes solved as Z3 integer variables with hierarchy and zone-fitting constraints; Skia pre-measurement ensures text fits before Z3 accepts a size; multi-solution enumeration creates variety
2. **Data shape analysis** — rule-based content type inference drives archetype-based template filtering
3. **Template as first-class model** — templates with archetype tags as metadata for filtering

## Commands

```bash
uv sync                                           # Install dependencies
uv add ...                                        # Add dependencies
uv run uvicorn server:app --reload --port 8002    # Run dev server
# Open http://localhost:8002

uv run pytest tests/ -x                           # Run e2e tests
uv run pytest tests/ -x --headed                  # Run e2e tests with visible browser
```

## Environment

Requires `ANTHROPIC_API_KEY` in `.env` for Claude ranking. Without it, ranking falls back to heuristic scoring. The full pipeline (data shape, Z3 solving, rendering) works without it.

## Architecture

### Pipeline (`runeform/pipeline.py`)

1. **Data shape** (`data_shape.py`) — Infers content type (single_event_hero, single_event_text, text_announcement) and density from input fields. Rule-based, no LLM.

2. **Template filter** (`compose.py:filter_templates`) — Filters 7 templates down to 2-3 by matching archetype tag to content type.

3. **Z3 typography** (`typography.py`) — For each template x font pairing, enumerates up to 8 distinct font size solutions. Each solution differs by at least 8px on the headline. Z3 unsat = template eliminated. This is the variety engine. Valid font sizes are pre-computed by measuring text bounding boxes with Skia — Z3 only considers sizes where the wrapped text actually fits the zone.

4. **Compose** (`compose.py`) — Crosses templates x font pairings x typography solutions x photos. Assigns content items to template zones.

5. **Score** (`scoring.py`) — Four heuristics (weight balance, focal hierarchy, breathing room, rule of thirds). Filters weak layouts before rendering.

6. **Render** (`render.py`) — Skia + HarfBuzz text shaping. Uses Z3-solved font sizes directly (no bisection). Photos scale-to-fill + center-crop. SVG logo support via Skia SVGDOM.

7. **Rank** (`ranking.py`) — Claude Haiku ranks rendered PNGs. Falls back to highest heuristic score.

### Font system (`runeform/fonts.py`)

- **FontFamily** — loads variable Google Fonts (.ttf), caches typefaces per weight via Skia VariationPosition
- **FontPairing** — headline + body families with element-type-based font/weight selection
- **4 curated pairings**: Editorial (Playfair+Inter), Modern (SpaceGrotesk+DMSans), Warm (DMSerif+SourceSans3), Clean (Inter+DMSans)
- **`measure_text_block()`** — word-wraps text and measures bounding box via Skia; used by Z3 to pre-compute valid font sizes per zone
- **`text_fits_zone()`** — checks if text at a given size fits within zone bounds

### Key models (`runeform/models.py`)

- `Template` — core primitive: name, label, archetype tag, zones, family
- `Zone` — bounds, visual_weight, allowed_elements, font_size_range
- `SolvedTypography` — Z3 output: font_sizes dict, satisfiable flag, solve time
- `DataShape` — content_type + ContentDensity
- `ComposedLayout` — template + placements (with solved font sizes) + typography + score

### Templates (`runeform/templates.py`)

7 templates, 1080x1080 canvas:
- `single_event_hero` (3): hero_left_text_right, hero_full_overlay, hero_top_text_bottom
- `single_event_text` (2): text_centered_stack, text_bold_title
- `text_announcement` (2): announcement_centered, announcement_split

Font size ranges: Headline 90-160px, Subhead 36-60px, Body 27-33px, Logo 27-33px.

### ESRGAN upscaling (`runeform/upscale.py`)

Low-res hero images are upscaled via Real-ESRGAN (spandrel + torch). Computed once per source image, cached as `{stem}_esrgan{ext}`.

### API (`server.py`)

- `GET /` — generate form
- `POST /generate` — HTML results page
- `POST /api/generate` — JSON API with `brand_zip` and `max_solutions` params
- `GET /brand` — brand kit form
- `POST /brand/save` — save brand kit
- `POST /brand/import` — import brand zip
- `GET /brand/export` — download brand zip

### Design principles

- Z3 is the variety engine, not just validation. It enumerates distinct typography solutions.
- Z3 zone fitting uses Skia bounding box measurement, not area heuristics. Text must actually fit.
- Zone positions are fixed by templates. Z3 only varies font sizes.
- Templates own spatial layout. Archetypes are filter tags on templates.
- Data shape is inferred before template selection. Content type drives filtering.
- Font rendering uses Skia + HarfBuzz with variable Google Fonts.
- Never distort images — scale-to-fill + center-crop.
- SVGs are rendered via Skia's SVGDOM.

## Dependencies

Key dependencies: `z3-solver`, `skia-python`, `fastapi`, `anthropic`, `spandrel`, `torch`.

Test extras: `pytest`, `playwright`, `pytest-playwright`.
