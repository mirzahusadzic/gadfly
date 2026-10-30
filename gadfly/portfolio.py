"""Several frames' verdicts side by side, without a verdict of their own.

`overall` reads one frame over its inputs. Different frames have different
relations, promises and recipients, and there is no fixed rule that combines
them, so a portfolio counts and groups: frames by category, open
obligations two or more frames share, and frames whose inputs disagree. It
never names a category for the portfolio.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Entry:
    """One frame's overall verdict, as `gadfly report --json` writes it."""

    name: str
    frame: str
    category: str
    inputs: dict[str, str]
    evidence: list[str] = field(default_factory=list)
    obligations: list[str] = field(default_factory=list)


def summarize(entries: list[Entry]) -> dict[str, Any]:
    """Counts by category, the frames in each, the obligations frames share,
    and the frames whose inputs reached different categories."""
    if not entries:
        raise ValueError("a portfolio needs at least one frame")
    names = [entry.name for entry in entries]
    if len(names) != len(set(names)):
        raise ValueError("portfolio entry names must be unique")
    counts = Counter(entry.category for entry in entries)
    by_category: dict[str, list[str]] = defaultdict(list)
    obligations: dict[str, list[str]] = defaultdict(list)
    input_disagreements: dict[str, dict[str, str]] = {}
    for entry in entries:
        by_category[entry.category].append(entry.name)
        for obligation in entry.obligations:
            obligations[obligation].append(entry.name)
        if len(set(entry.inputs.values())) > 1:
            input_disagreements[entry.name] = entry.inputs
    return {
        "frames": len(entries),
        "categories": dict(sorted(counts.items())),
        "by_category": dict(sorted(by_category.items())),
        "shared_obligations": {
            text: frames for text, frames in sorted(obligations.items()) if len(frames) > 1
        },
        "input_disagreements": input_disagreements,
    }


def entry_from(document: dict[str, Any]) -> Entry:
    """An entry from a `gadfly report --json` document (or a bare overall)."""
    overall = document.get("overall", document)
    return Entry(
        name=document.get("frame", document.get("name", "unnamed")),
        frame=document.get("hash", ""),
        category=overall["category"],
        inputs=overall.get("inputs", {}),
        evidence=list(overall.get("evidence", [])),
        obligations=list(overall.get("obligations", [])),
    )
