"""The admissible interventions Δ: each changes or removes the relation and
keeps everything else as it was.

Every trial body is derived from the frame alone, so the plan is fixed, and
recorded, before a single observation is made; the sham's draw is seeded by
the frame's hash, never by the clock.
"""

from __future__ import annotations

import functools
import random
import re
from bisect import bisect_left, bisect_right
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

from .frame import Frame, Span, digest


@dataclass(frozen=True)
class Trial:
    """One intervention, applied: the body the scorer will read."""

    id: str  # baseline, repeat, ablation, ablation-<anchor>, cumulative, sham-1, ...
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


def place(spans: tuple[Span, ...], span_id: str, after: str) -> tuple[Span, ...]:
    """The spans with one moved to follow another; every text unchanged."""
    moving = next(span for span in spans if span.id == span_id)
    rest = [span for span in spans if span.id != span_id]
    at = next(i for i, span in enumerate(rest) if span.id == after) + 1
    return (*rest[:at], moving, *rest[at:])


def without(spans: tuple[Span, ...], removed: set[str]) -> tuple[Span, ...]:
    """The spans, in their order, less those named."""
    return tuple(span for span in spans if span.id not in removed)


def rename(text: str, mapping: tuple[tuple[str, str], ...]) -> str:
    """Rename each word consistently, whole words only, in one pass: a word is
    renamed once (a swap stays a swap), and a phrase wins over a word inside
    it. A capital is kept, and so is a word written in capitals. A word may
    begin or end in a sign, such as 20% or C++; it is never part of a longer
    word."""
    return renamer(mapping)(text) if mapping else text


@lru_cache(maxsize=64)
def renamer(mapping: tuple[tuple[str, str], ...]) -> Callable[[str], str]:
    """`rename` with its map built once: the table and the pattern are made
    here, and the function returned applies them to any text."""
    table = {old.lower(): new for old, new in mapping}
    words = "|".join(re.escape(old) for old in sorted(table, key=len, reverse=True))
    # whole words: no letter, digit or underscore just before or after, which
    # holds at a sign as well as at a letter (\b would need one beyond "%")
    pattern = re.compile(rf"(?<!\w)(?:{words})(?!\w)", flags=re.IGNORECASE)

    def swap(match: re.Match[str]) -> str:
        word = match.group(0)
        new = table[word.lower()]
        if word.isupper() and sum(c.isalpha() for c in word) > 1:
            return new.upper()
        return new[:1].upper() + new[1:] if word[:1].isupper() else new

    return lambda text: pattern.sub(swap, text)


def sham_draws(frame: Frame, count: int) -> list[tuple[str, ...]]:
    """Spans to remove instead of the anchors: as many as the anchors, of the
    same kinds, none cited, none bypassed, none a declared fallback, and no
    span in two draws. A fallback is declared to carry the relation, so
    cutting it is no sham. Each is the closest in length still free; spans
    equally close are drawn among by the frame's own seed. A draw that
    cannot be matched is left out; the verdict says so."""
    iv = frame.interventions
    anchored = set(frame.anchors)  # looked up, not scanned
    # what a sham may not cut
    kept = anchored | set(iv.get("bypass") or []) | set(iv.get("cumulative") or [])
    # Free spans by kind, each pool sorted by length then body order, once.
    pools: dict[str, list[tuple[int, int, Span]]] = defaultdict(list)
    for at, span in enumerate(frame.spans):
        if span.id not in kept:
            pools[span.kind].append((len(span.text), at, span))
    for pool in pools.values():
        pool.sort(key=lambda entry: entry[:2])
    # each pool's lengths, kept beside it, so a draw never rebuilds them
    lengths = {kind: [entry[0] for entry in pool] for kind, pool in pools.items()}
    anchors = [span for span in frame.spans if span.id in anchored]
    rng = random.Random(int(frame.hash[:16], 16))
    draws: list[tuple[str, ...]] = []
    for _ in range(count):
        chosen: list[str] = []
        for anchor in anchors:
            pool = pools.get(anchor.kind)
            if not pool:
                return draws
            at = _nearest(pool, lengths[anchor.kind], len(anchor.text), rng)
            lengths[anchor.kind].pop(at)
            chosen.append(pool.pop(at)[2].id)
        draws.append(tuple(sorted(chosen)))
    return draws


@functools.lru_cache(maxsize=64)
def _drawn(frame: Frame, count: int) -> tuple[tuple[str, ...], ...]:
    """A frame's sham draws, made once: counting, planning and running a frame
    each need them, and among many equally near spans each draw is costly."""
    return tuple(sham_draws(frame, count))


def _nearest(
    pool: list[tuple[int, int, Span]], lengths: list[int], length: int, rng: random.Random
) -> int:
    """The index of the span in `pool` closest to `length`, given the pool's
    lengths. The equally close lie side by side in the sorted pool; the seed
    chooses among them."""
    at = bisect_left(lengths, length)
    best = min(abs(lengths[i] - length) for i in (at - 1, at) if 0 <= i < len(pool))
    lo, hi = bisect_left(lengths, length - best), bisect_right(lengths, length + best)
    if hi - lo == 1:
        return lo
    return min(range(lo, hi), key=lambda i: (rng.random(), pool[i][1]))


# A trial's id where it differs from its key in the frame
TRIAL_IDS = {"inputInversion": "input-inversion"}


def trial_ids(frame: Frame) -> list[str]:
    """The ids `plan` gives its trials, in its order, without building any
    trial's body: what a budget is counted from."""
    iv = frame.interventions
    ids = ["baseline", *(["repeat"] if iv.get("repeat") else []), "ablation"]
    if iv.get("eachAnchor"):
        ids += [f"ablation-{anchor}" for anchor in frame.anchors]
    if iv.get("cumulative"):
        ids.append("cumulative")
    sham = iv.get("sham")
    if sham:
        count = 1 if sham is True else sham["draws"]
        ids += [f"sham-{index}" for index in range(1, len(_drawn(frame, count)) + 1)]
    kinds = ("presentation", "placement", "inversion", "inputInversion", "bypass", "control")
    ids += [TRIAL_IDS.get(kind, kind) for kind in kinds if iv.get(kind)]
    return ids


def plan(frame: Frame) -> list[Trial]:
    """The trials of one input, in a fixed order."""
    spans, iv = frame.spans, frame.interventions
    trials = [Trial("baseline", "baseline", (), (), spans)]
    if iv.get("repeat"):
        trials.append(Trial("repeat", "repeat", (), (), spans))
    removed = tuple(frame.anchors)
    trials.append(Trial("ablation", "ablation", removed, (), without(spans, set(removed))))
    if iv.get("eachAnchor"):
        # each anchor cut alone: how the anchors carry what the ablation moved
        for anchor in removed:
            cut = without(spans, {anchor})
            trials.append(Trial(f"ablation-{anchor}", "each-anchor", (anchor,), (), cut))
    if iv.get("cumulative"):
        more = tuple(sorted(set(removed) | set(iv["cumulative"])))
        trials.append(Trial("cumulative", "cumulative", more, (), without(spans, set(more))))
    sham = iv.get("sham")
    if sham:
        count = 1 if sham is True else sham["draws"]
        for index, draw in enumerate(_drawn(frame, count), start=1):
            trials.append(Trial(f"sham-{index}", "sham", draw, (), without(spans, set(draw))))
    if iv.get("presentation"):
        mapping = tuple(sorted(iv["presentation"].items()))
        renaming = renamer(mapping)
        renamed = tuple(Span(span.id, renaming(span.text), span.kind) for span in spans)
        trials.append(Trial("presentation", "presentation", (), mapping, renamed))
    if iv.get("placement"):
        moved = place(spans, iv["placement"]["span"], iv["placement"]["after"])
        trials.append(Trial("placement", "placement", (), (), moved))
    if iv.get("inversion"):
        mapping = tuple(sorted(iv["inversion"].items()))
        inverting = renamer(mapping)
        inverted = tuple(Span(span.id, inverting(span.text), span.kind) for span in spans)
        trials.append(Trial("inversion", "inversion", (), mapping, inverted))
    if iv.get("inputInversion"):
        # what is asked turns; the evidence stays as it is
        mapping = tuple(sorted(iv["inputInversion"].items()))
        trials.append(Trial("input-inversion", "input-inversion", (), mapping, spans))
    if iv.get("bypass"):
        cut = tuple(iv["bypass"])
        trials.append(Trial("bypass", "bypass", cut, (), without(spans, set(cut))))
    if iv.get("control"):
        cut = tuple(iv["control"])
        trials.append(Trial("control", "control", cut, (), without(spans, set(cut))))
    return trials


def prompt(frame: Frame, trial: Trial, x: dict[str, str]) -> str:
    """What the scorer reads: the trial's body and one input, nothing else.
    Presentation renames the input's words too, so only the wording moves;
    an inversion changes the relation's sense in the body alone, and an input
    inversion what is asked alone."""
    renames = trial.kind in ("presentation", "input-inversion") and trial.renamed
    question = rename(x["text"], trial.renamed) if renames else x["text"]
    return f"{trial.text}\n\n---\n\n{question}"
