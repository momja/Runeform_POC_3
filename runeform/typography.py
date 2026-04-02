"""Z3 typography constraint solver — the variety engine.

Solves font sizes for text zones within a template, respecting:
- Zone bounds (text must fit)
- Hierarchy (headline > subhead > body)
- Step size (multiples of 2)

Enumerates multiple distinct solutions per template by blocking previous
solutions and requiring a minimum headline difference. Each solution is
a different visual treatment of the same template+content.
"""

import time

import z3

from .fonts import FontMetrics, FontPairing, get_pairing
from .models import (
    ContentItem,
    ElementType,
    FontSizeRange,
    SolvedTypography,
    Template,
    Zone,
)

ZONE_PADDING = 20  # px padding inside zone bounds

# Hierarchy ordering (higher in list = larger font required)
HIERARCHY = [ElementType.HEADLINE, ElementType.SUBHEAD, ElementType.BODY]
MIN_HIERARCHY_GAP = 3  # minimum px difference between levels

# Multi-solution parameters
DEFAULT_MAX_SOLUTIONS = 3
MIN_HEADLINE_DIFF = 8  # minimum headline size difference between solutions


def _build_solver(
    template: Template,
    content_by_zone: dict[str, ContentItem],
    pairing: FontPairing | None = None,
) -> tuple[z3.Solver, dict[str, z3.ArithRef], list[tuple[ElementType, z3.ArithRef]]]:
    """Build the Z3 solver with all constraints. Returns (solver, size_vars, hierarchy_vars).

    When a font pairing is provided, uses actual per-font metrics for zone
    fitting constraints instead of hardcoded approximations.
    """
    solver = z3.Solver()
    solver.set("timeout", 2000)

    size_vars: dict[str, z3.ArithRef] = {}
    zone_element_types: dict[str, ElementType] = {}

    for zone in template.zones:
        if zone.name not in content_by_zone:
            continue
        content = content_by_zone[zone.name]
        if content.element_type == ElementType.HERO:
            continue
        if not content.text:
            continue

        fsr = zone.font_size_range or FontSizeRange()
        var = z3.Int(f"font_{zone.name}")
        size_vars[zone.name] = var
        zone_element_types[zone.name] = content.element_type

        # Zone fitting constraint: pre-measure with Skia to find valid sizes.
        # The Or of valid sizes replaces separate bound/step constraints.
        text = content.text
        if pairing and text:
            valid_sizes = []
            for sz in range(fsr.min_size, fsr.max_size + 1, fsr.step):
                if pairing.text_fits_zone(
                    text, content.element_type.value, sz,
                    zone.bounds.width, zone.bounds.height, ZONE_PADDING,
                ):
                    valid_sizes.append(sz)
            if valid_sizes:
                solver.add(z3.Or(*[var == sz for sz in valid_sizes]))
            else:
                solver.add(False)  # No valid size — force unsat
        else:
            # Fallback: bound + step + area approximation when no pairing
            solver.add(var >= fsr.min_size)
            solver.add(var <= fsr.max_size)
            solver.add(var % fsr.step == 0)
            text_len = max(len(text or ""), 1)
            usable_w = max(zone.bounds.width - ZONE_PADDING, 1)
            usable_h = max(zone.bounds.height - ZONE_PADDING, 1)
            scale = 1000
            cwr = 600  # 0.60 * 1000
            lhr = 1350  # 1.35 * 1000
            lhs = text_len * cwr * lhr * var * var
            rhs = int(usable_w * usable_h) * scale * scale
            solver.add(lhs <= rhs)

    # Hierarchy constraints
    hierarchy_vars: list[tuple[ElementType, z3.ArithRef]] = []
    for et in HIERARCHY:
        for zone_name, var in size_vars.items():
            if zone_element_types.get(zone_name) == et:
                hierarchy_vars.append((et, var))
                break

    for i in range(len(hierarchy_vars) - 1):
        _, var_higher = hierarchy_vars[i]
        _, var_lower = hierarchy_vars[i + 1]
        solver.add(var_higher > var_lower)
        solver.add(var_higher - var_lower >= MIN_HIERARCHY_GAP)

    return solver, size_vars, hierarchy_vars


def _extract_solution(
    solver: z3.Solver,
    size_vars: dict[str, z3.ArithRef],
) -> dict[str, int] | None:
    """Check sat and extract font sizes from the model. Returns None if unsat."""
    result = solver.check()
    if result != z3.sat:
        return None
    model = solver.model()
    return {name: model[var].as_long() for name, var in size_vars.items()}


def solve_typography(
    template: Template,
    content_by_zone: dict[str, ContentItem],
    max_solutions: int = DEFAULT_MAX_SOLUTIONS,
    min_headline_diff: int = MIN_HEADLINE_DIFF,
    pairing: FontPairing | None = None,
) -> list[SolvedTypography]:
    """Enumerate up to max_solutions distinct typography solutions for a template.

    Each solution differs from all previous ones by at least min_headline_diff
    on the headline font size. When a font pairing is provided, Z3 uses actual
    measured metrics for that pairing's fonts. Returns an empty list if the first
    solve is unsat (meaning the template cannot render this content at all).
    """
    if pairing is None:
        pairing = get_pairing()
    start = time.monotonic()
    solver, size_vars, hierarchy_vars = _build_solver(template, content_by_zone, pairing)

    if not size_vars:
        # No text zones to solve (e.g., image-only template)
        elapsed = (time.monotonic() - start) * 1000
        return [SolvedTypography(font_sizes={}, satisfiable=True, solve_time_ms=elapsed)]

    # Find the headline variable for distinctness constraints
    headline_var: z3.ArithRef | None = None
    for zone_name, var in size_vars.items():
        # The headline zone typically has "headline" in the name
        for zone in template.zones:
            if zone.name == zone_name and ElementType.HEADLINE in zone.allowed_elements:
                headline_var = var
                break
        if headline_var is not None:
            break

    solutions: list[SolvedTypography] = []
    previous_headline_sizes: list[int] = []

    for i in range(max_solutions):
        font_sizes = _extract_solution(solver, size_vars)
        elapsed = (time.monotonic() - start) * 1000

        if font_sizes is None:
            if i == 0:
                # First solve is unsat — template cannot render this content
                return [SolvedTypography(font_sizes={}, satisfiable=False, solve_time_ms=elapsed)]
            break  # No more solutions

        solutions.append(SolvedTypography(
            font_sizes=font_sizes,
            satisfiable=True,
            solve_time_ms=elapsed,
        ))

        if headline_var is None:
            break  # Can't enforce distinctness without a headline variable

        # Block this solution and require the next to be distinct
        headline_size = font_sizes.get(
            next(
                zn for zn in size_vars
                if any(z.name == zn and ElementType.HEADLINE in z.allowed_elements
                       for z in template.zones)
            ),
        )
        if headline_size is None:
            break

        previous_headline_sizes.append(headline_size)

        # Add distinctness constraint: headline must differ from ALL previous
        # solutions by at least min_headline_diff
        for prev_size in previous_headline_sizes:
            solver.add(z3.Or(
                headline_var <= prev_size - min_headline_diff,
                headline_var >= prev_size + min_headline_diff,
            ))

    return solutions
