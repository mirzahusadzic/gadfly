"""The admissible interventions Δ: each changes or removes the relation and
keeps everything else as it was.

Every trial body is derived from the frame alone, so the plan is fixed, and
recorded, before a single observation is made; the sham's draw is seeded by
the frame's hash, never by the clock.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from .frame import Frame, Span, digest


@dataclass(frozen=True)
class Trial:
    """One intervention, applied: the body the scorer will read."""

    id: str  # baseline, repeat, ablation, cumulative, sham-1, presentation, bypass, control
    kind: str
    removed: tuple[str, ...]
    renamed: tuple[tuple[str, str], ...]
    spans: tuple[Span, ...]

    @property
    def text(self) -> str:
        return "\n".join(span.text for span in self.spans)

    @property
    def body_hash(self) -> str:
        return digest([[span.id, span.text] for span in self.spans])


def without(spans: tuple[Span, ...], removed: set[str]) -> tuple[Span, ...]:
    return tuple(span for span in spans if span.id not in removed)


def rename(text: str, mapping: tuple[tuple[str, str], ...]) -> str:
    """Rename each word consistently, whole words only, in one pass: a word is
    renamed once (a swap stays a swap), and a phrase wins over a word inside
    it. A capital is kept, and so is a word written in capitals."""
    if not mapping:
        return text
    table = {old.lower(): new for old, new in mapping}
    words = "|".join(re.escape(old) for old in sorted(table, key=len, reverse=True))

    def swap(match: re.Match[str]) -> str:
        word = match.group(0)
        new = table[word.lower()]
        if word.isupper() and sum(c.isalpha() for c in word) > 1:
            return new.upper()
        return new[:1].upper() + new[1:] if word[:1].isupper() else new

    return re.sub(rf"\b(?:{words})\b", swap, text, flags=re.IGNORECASE)


def sham_draws(frame: Frame, count: int) -> list[tuple[str, ...]]:
    """Spans to remove instead of the anchors: as many as the anchors, of the
    same kinds, none cited, none bypassed, and no span in two draws. Each is
    the closest in length still free, ties broken by the frame's own seed. A
    draw that cannot be matched is left out; the verdict says so."""
    anchors = [span for span in frame.spans if span.id in frame.anchors]
    bypassed = set(frame.interventions.get("bypass") or [])
    free = [
        span for span in frame.spans if span.id not in frame.anchors and span.id not in bypassed
    ]
    rng = random.Random(int(frame.hash[:16], 16))
    draws: list[tuple[str, ...]] = []
    for _ in range(count):
        chosen: list[str] = []
        for anchor in anchors:
            options = [span for span in free if span.kind == anchor.kind and span.id not in chosen]
            if not options:
                return draws
            options.sort(key=lambda span: (abs(len(span.text) - len(anchor.text)), rng.random()))
            chosen.append(options[0].id)
        free = [span for span in free if span.id not in chosen]
        draws.append(tuple(sorted(chosen)))
    return draws


def plan(frame: Frame) -> list[Trial]:
    """The trials of one input, in a fixed order."""
    spans, iv = frame.spans, frame.interventions
    trials = [Trial("baseline", "baseline", (), (), spans)]
    if iv.get("repeat"):
        trials.append(Trial("repeat", "repeat", (), (), spans))
    removed = tuple(frame.anchors)
    trials.append(Trial("ablation", "ablation", removed, (), without(spans, set(removed))))
    if iv.get("cumulative"):
        more = tuple(sorted(set(removed) | set(iv["cumulative"])))
        trials.append(Trial("cumulative", "cumulative", more, (), without(spans, set(more))))
    sham = iv.get("sham")
    if sham:
        count = 1 if sham is True else sham["draws"]
        for index, draw in enumerate(sham_draws(frame, count), start=1):
            trials.append(Trial(f"sham-{index}", "sham", draw, (), without(spans, set(draw))))
    if iv.get("presentation"):
        mapping = tuple(sorted(iv["presentation"].items()))
        renamed = tuple(Span(span.id, rename(span.text, mapping), span.kind) for span in spans)
        trials.append(Trial("presentation", "presentation", (), mapping, renamed))
    if iv.get("bypass"):
        cut = tuple(iv["bypass"])
        trials.append(Trial("bypass", "bypass", cut, (), without(spans, set(cut))))
    if iv.get("control"):
        cut = tuple(iv["control"])
        trials.append(Trial("control", "control", cut, (), without(spans, set(cut))))
    return trials


def prompt(frame: Frame, trial: Trial, x: dict[str, str]) -> str:
    """What the scorer reads: the trial's body and one input, nothing else.
    Presentation renames the input's words too, so only the wording moves."""
    question = rename(x["text"], trial.renamed) if trial.renamed else x["text"]
    return f"{trial.text}\n\n---\n\n{question}"
