"""Pre-LLM compositional heuristics.

Lightweight scoring to filter weak layouts before the expensive Claude call.
"""

from .models import ComposedLayout
from .templates import CANVAS_H, CANVAS_W


def _weight_balance(layout: ComposedLayout) -> float:
    """Score how well visual weight is distributed across the canvas."""
    left_weight = 0.0
    right_weight = 0.0
    top_weight = 0.0
    bottom_weight = 0.0
    cx, cy = CANVAS_W / 2, CANVAS_H / 2

    for p in layout.placements:
        zone_cx = p.zone.bounds.x + p.zone.bounds.width / 2
        zone_cy = p.zone.bounds.y + p.zone.bounds.height / 2
        w = p.zone.visual_weight

        if zone_cx < cx:
            left_weight += w
        else:
            right_weight += w

        if zone_cy < cy:
            top_weight += w
        else:
            bottom_weight += w

    total = left_weight + right_weight
    if total == 0:
        return 0.0

    lr_balance = 1.0 - abs(left_weight - right_weight) / total
    tb_balance = 1.0 - abs(top_weight - bottom_weight) / total
    return (lr_balance + tb_balance) / 2


def _focal_hierarchy(layout: ComposedLayout) -> float:
    """Score whether the highest visual-weight zone is largest on canvas."""
    if not layout.placements:
        return 0.0

    by_weight = sorted(layout.placements, key=lambda p: p.zone.visual_weight, reverse=True)
    by_area = sorted(
        layout.placements,
        key=lambda p: p.zone.bounds.width * p.zone.bounds.height,
        reverse=True,
    )

    if by_weight[0].zone.name == by_area[0].zone.name:
        return 1.0
    elif len(by_weight) > 1 and by_weight[0].zone.name == by_area[1].zone.name:
        return 0.6
    return 0.3


def _breathing_room(layout: ComposedLayout) -> float:
    """Score how much whitespace exists between zones."""
    zones = [p.zone.bounds for p in layout.placements]
    if len(zones) < 2:
        return 1.0

    total_zone_area = sum(z.width * z.height for z in zones)
    canvas_area = CANVAS_W * CANVAS_H
    coverage = total_zone_area / canvas_area

    if 0.5 <= coverage <= 0.75:
        return 1.0
    elif coverage < 0.5:
        return 0.6 + coverage * 0.8
    else:
        return max(0.3, 1.0 - (coverage - 0.75) * 2)


def _rule_of_thirds(layout: ComposedLayout) -> float:
    """Score proximity of focal elements to rule-of-thirds intersections."""
    thirds_x = [CANVAS_W / 3, 2 * CANVAS_W / 3]
    thirds_y = [CANVAS_H / 3, 2 * CANVAS_H / 3]

    if not layout.placements:
        return 0.0

    focal = max(layout.placements, key=lambda p: p.zone.visual_weight)
    zone_cx = focal.zone.bounds.x + focal.zone.bounds.width / 2
    zone_cy = focal.zone.bounds.y + focal.zone.bounds.height / 2

    min_dist_x = min(abs(zone_cx - tx) for tx in thirds_x)
    min_dist_y = min(abs(zone_cy - ty) for ty in thirds_y)

    norm_dist = (min_dist_x / CANVAS_W + min_dist_y / CANVAS_H) / 2
    return max(0.0, 1.0 - norm_dist * 3)


def score_layout(layout: ComposedLayout) -> float:
    """Composite heuristic score (0-1)."""
    weights = {
        "balance": 0.25,
        "hierarchy": 0.30,
        "breathing": 0.25,
        "thirds": 0.20,
    }
    scores = {
        "balance": _weight_balance(layout),
        "hierarchy": _focal_hierarchy(layout),
        "breathing": _breathing_room(layout),
        "thirds": _rule_of_thirds(layout),
    }
    return sum(scores[k] * weights[k] for k in weights)


def filter_and_score(
    layouts: list[ComposedLayout],
    min_score: float = 0.3,
) -> list[ComposedLayout]:
    """Score all layouts and filter out weak ones."""
    for layout in layouts:
        layout.heuristic_score = score_layout(layout)

    scored = [l for l in layouts if l.heuristic_score >= min_score]
    scored.sort(key=lambda l: l.heuristic_score, reverse=True)
    return scored
