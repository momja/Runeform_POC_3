# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## What this is

Runeform POC 3 — a compositional layout engine for brand marketing. This proof of concept demonstrates three architectural concepts:

1. **Z3 typography constraint solving** — font sizes solved as Z3 integer variables with hierarchy and zone-fitting constraints; multi-solution enumeration creates variety
2. **Data shape analysis** — rule-based content type inference drives archetype-based template filtering
3. **Template as first-class model** — templates with archetype tags as metadata for filtering

## Commands

```bash
uv sync                                           # Install dependencies
uv add ...                                        # Add dependencies
uv run uvicorn server:app --reload --port 8002    # Run dev server
# Open http://localhost:8002
```

No test suite. No linter configured.

## Environment

Requires `ANTHROPIC_API_KEY` in `.env` for Claude ranking. Without it, ranking falls back to heuristic scoring. The full pipeline (data shape, Z3 solving, rendering) works without it.

## Architecture

### Pipeline (`runeform/pipeline.py`)

1. **Data shape** (`data_shape.py`) — Infers content type (single_event_hero, single_event_text, text_announcement) and density from input fields. Rule-based, no LLM.

2. **Template filter** (`compose.py:filter_templates`) — Filters 7 templates down to 2-3 by matching archetype tag to content type.

3. **Z3 typography** (`typography.py`) — For each template, enumerates up to 3 distinct font size solutions. Each solution differs by at least 8px on the headline. Z3 unsat = template eliminated. This is the variety engine.

4. **Compose** (`compose.py`) — Crosses templates x typography solutions x photos. Assigns content items to template zones.

5. **Score** (`scoring.py`) — Four heuristics (weight balance, focal hierarchy, breathing room, rule of thirds). Filters weak layouts before rendering.

6. **Render** (`render.py`) — Pillow-based. Uses Z3-solved font sizes directly (no bisection). Photos scale-to-fill + center-crop.

7. **Rank** (`ranking.py`) — Claude Haiku ranks rendered PNGs. Falls back to highest heuristic score.

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

### Design principles

- Z3 is the variety engine, not just validation. It enumerates distinct typography solutions.
- Zone positions are fixed by templates. Z3 only varies font sizes.
- Templates own spatial layout. Archetypes are filter tags on templates.
- Data shape is inferred before template selection. Content type drives filtering.
- Font rendering assumes macOS Helvetica with fallback to default.
- Never distort images — scale-to-fill + center-crop.

## Dependencies

Key new dependency vs POC 1/2: `z3-solver`.
