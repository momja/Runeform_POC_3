"""End-to-end generation pipeline.

1. Parse event data from structured form fields
2. Analyze data shape (content type + density)
3. Filter templates by archetype tag
4. For each template: Z3 enumerate typography solutions
5. For each (template x typography x photo): compose layout
6. Heuristic score + filter
7. Render survivors
8. LLM rank
"""

from pathlib import Path

from .compose import build_content_by_zone, build_content_items, compose, filter_templates
from .data_shape import analyze_data_shape
from .fonts import get_pairing, list_pairings
from .models import BrandKit, EventData, GenerationResult, PhotoCandidate
from .photos import retrieve_photos
from .ranking import rank
from .render import render_all
from .scoring import filter_and_score
from .templates import ALL_TEMPLATES
from .typography import solve_typography
from .upscale import upscale_if_needed

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def generate(
    event: EventData,
    brand: BrandKit | None = None,
    top_k_photos: int = 8,
    max_typo_solutions: int = 8,
) -> GenerationResult:
    """Run the full generation pipeline."""

    templates_considered = len(ALL_TEMPLATES)

    # 1. Determine image availability
    has_uploaded_image = event.image_path is not None and event.image_path.exists()

    # 2. Analyze data shape
    data_shape = analyze_data_shape(event, has_uploaded_image)
    print(f"[pipeline] Data shape: {data_shape.content_type.value} "
          f"(density: title={data_shape.density.title_length}, "
          f"fields={data_shape.density.field_count})")

    # 3. Filter templates by archetype tag
    templates = filter_templates(ALL_TEMPLATES, data_shape)
    templates_after_filter = len(templates)
    print(f"[pipeline] Templates: {templates_considered} total -> "
          f"{templates_after_filter} after archetype filter "
          f"({[t.name for t in templates]})")

    # 4. Source photos
    photos: list[PhotoCandidate] = []
    if has_uploaded_image:
        photos = [PhotoCandidate(
            asset_id="uploaded",
            score=1.0,
            label="Uploaded Image",
            path=event.image_path,
        )]
    elif data_shape.content_type.value == "single_event_hero":
        event_context = _build_context(event)
        photos = retrieve_photos(event_context, top_k=top_k_photos)
    else:
        # Text-only templates don't need photos
        photos = [PhotoCandidate(asset_id="none", score=1.0, label="No Photo")]

    print(f"[pipeline] Photos: {len(photos)} candidates")

    # 4b. ESRGAN upscale low-res photos (once per source, cached)
    for photo in photos:
        if photo.path and photo.path.exists():
            photo.path = upscale_if_needed(photo.path)

    # 5. Build subtitle from event fields
    subtitle_parts = []
    if event.date:
        subtitle_parts.append(event.date)
    if event.time:
        subtitle_parts.append(event.time)
    if event.location:
        subtitle_parts.append(event.location)
    subtitle = " | ".join(subtitle_parts) if subtitle_parts else None

    # 6. For each (template × font pairing): Z3 enumerate typography solutions,
    #    then cross with photos. Z3 uses actual font metrics per pairing.
    all_layouts = []
    layout_pairings = []  # parallel list: which pairing was used per layout
    templates_with_solutions = 0
    pairing_names = list_pairings()

    for template in templates:
        content_items = build_content_items(
            title=event.title,
            subtitle=subtitle,
            body=event.description,
            brand=brand,
        )
        content_by_zone = build_content_by_zone(template, content_items)

        template_has_solution = False
        for pairing_name in pairing_names:
            pairing = get_pairing(pairing_name)

            typo_solutions = solve_typography(
                template, content_by_zone,
                max_solutions=max_typo_solutions,
                pairing=pairing,
            )

            if not typo_solutions or not typo_solutions[0].satisfiable:
                print(f"[pipeline] Template '{template.name}' + {pairing_name}: Z3 unsat")
                continue

            template_has_solution = True
            valid_solutions = [s for s in typo_solutions if s.satisfiable]
            print(f"[pipeline] Template '{template.name}' + {pairing_name}: "
                  f"{len(valid_solutions)} solutions")

            for sol in valid_solutions:
                print(f"  -> {sol.font_sizes} ({sol.solve_time_ms:.0f}ms)")

            for photo in photos:
                content_items_with_photo = build_content_items(
                    title=event.title,
                    subtitle=subtitle,
                    body=event.description,
                    photo=photo if photo.path else None,
                    brand=brand,
                )
                for sol in valid_solutions:
                    layout = compose(template, content_items_with_photo, sol)
                    all_layouts.append(layout)
                    layout_pairings.append(pairing)

        if template_has_solution:
            templates_with_solutions += 1

    templates_after_z3 = templates_with_solutions
    print(f"[pipeline] After Z3: {templates_after_z3} templates, "
          f"{len(all_layouts)} total candidates across {len(pairing_names)} pairings")

    if not all_layouts:
        # No valid layouts at all — return empty result
        return GenerationResult(
            layouts=[],
            rendered_paths=[],
            best_index=0,
            reasoning="No valid layouts could be generated for this content.",
            data_shape=data_shape,
            templates_considered=templates_considered,
            templates_after_filter=templates_after_filter,
            templates_after_z3=templates_after_z3,
        )

    # 7. Heuristic score + filter (preserve pairing mapping)
    scored_with_pairings = list(zip(all_layouts, layout_pairings))
    scored_layouts = filter_and_score(all_layouts, min_score=0.2)
    # Rebuild pairing list for scored layouts (filter_and_score preserves order)
    scored_set = set(id(l) for l in scored_layouts)
    scored_pairings = [p for l, p in scored_with_pairings if id(l) in scored_set]
    print(f"[pipeline] After scoring: {len(scored_layouts)} layouts (from {len(all_layouts)})")

    # 8. Render each layout with its corresponding font pairing
    OUTPUT_DIR.mkdir(exist_ok=True)
    paths = []
    for i, (layout, pairing) in enumerate(zip(scored_layouts, scored_pairings), 1):
        from .render import render_layout
        path = render_layout(layout, i, OUTPUT_DIR, brand=brand, pairing=pairing)
        paths.append(path)
    print(f"[pipeline] Rendered {len(paths)} images")
    scored = scored_layouts

    # 9. Rank
    event_context = _build_context(event)
    best_i, reasoning = rank(paths, scored, event_context)
    print(f"[pipeline] Best: #{best_i + 1} — {reasoning}")

    return GenerationResult(
        layouts=scored,
        rendered_paths=paths,
        best_index=best_i,
        reasoning=reasoning,
        data_shape=data_shape,
        templates_considered=templates_considered,
        templates_after_filter=templates_after_filter,
        templates_after_z3=templates_after_z3,
    )


def _build_context(event: EventData) -> str:
    """Build a text description for photo retrieval and ranking."""
    parts = [event.title]
    if event.date:
        parts.append(f"Date: {event.date}")
    if event.time:
        parts.append(f"Time: {event.time}")
    if event.location:
        parts.append(f"Location: {event.location}")
    if event.description:
        parts.append(event.description)
    if event.category:
        parts.append(f"Category: {event.category}")
    return " | ".join(parts)
