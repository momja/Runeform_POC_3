"""LLM ranking — send rendered PNGs to Claude for aesthetic evaluation.

Falls back to heuristic-based ranking if no API key is available.
"""

import base64
import json
import os
from pathlib import Path

from .models import ComposedLayout


def rank_with_claude(
    paths: list[Path],
    layouts: list[ComposedLayout],
    event_context: str,
) -> tuple[int, str]:
    """Send layout images to Claude for ranking. Returns (best_0indexed, reasoning)."""
    import anthropic

    client = anthropic.Anthropic()

    content: list[dict] = []
    for i, path in enumerate(paths, 1):
        label = layouts[i - 1].template.label
        typo = layouts[i - 1].typography.font_sizes
        content.append({
            "type": "text",
            "text": f"Layout {i} ({label}, typography: {typo}):",
        })
        with open(path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode()
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": data},
        })

    content.append({
        "type": "text",
        "text": f"""You are a graphic design critic evaluating {len(paths)} layout options
for a marketing poster for a small venue.

Event context: {event_context}

Each layout uses a different compositional template and/or typography solution.
Some layouts share the same template but differ in font sizes (headline, subhead, body).

Rank the layouts on:
  1. Visual hierarchy — eye naturally finds the headline first
  2. Composition balance — elements well-distributed, no awkward clustering
  3. Whitespace quality — breathing room without feeling empty
  4. Typography quality — font sizes feel appropriate and harmonious
  5. Contextual fit — does the layout feel appropriate for this type of event?

Reply with ONLY valid JSON — no markdown, no extra text:
{{"best": <number 1-{len(paths)}>, "reasoning": "<one concise sentence>"}}""",
    })

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": content}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
        text = text.strip()
    result = json.loads(text[text.find("{"):text.rfind("}") + 1])
    best = result["best"] - 1
    reasoning = result.get("reasoning", "")
    return best, reasoning


def rank_by_heuristic(layouts: list[ComposedLayout]) -> tuple[int, str]:
    """Fallback: pick the layout with the highest heuristic score."""
    if not layouts:
        return 0, "No layouts to rank"
    best_i = max(range(len(layouts)), key=lambda i: layouts[i].heuristic_score)
    return best_i, f"Selected by heuristic score ({layouts[best_i].heuristic_score:.2f})"


def rank(
    paths: list[Path],
    layouts: list[ComposedLayout],
    event_context: str,
) -> tuple[int, str]:
    """Rank layouts, using Claude if available, otherwise heuristic fallback."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return rank_with_claude(paths, layouts, event_context)
        except Exception as e:
            print(f"Claude ranking failed ({e}), falling back to heuristic")
            return rank_by_heuristic(layouts)
    else:
        return rank_by_heuristic(layouts)
