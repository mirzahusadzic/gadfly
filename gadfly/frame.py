"""The frame you declare: the situated relation (L) and its assessment frame (Γ).

A frame is plain JSON. It is read whole, checked, and hashed in a canonical
form before any trial runs; the hash travels with every record, so a verdict
always names the frame it was read under. Changing any coordinate, the grain
included, gives another hash: another frame.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# The situated relation L = (I, B, r, g, P, T, B0, C, p): each must be said
# (the body B and the baseline B0 are checked on their own).
SITUATION = ("relation", "locus", "role", "grain", "purpose", "trajectory", "crossing", "promise")
INTERVENTIONS = ("repeat", "ablation", "cumulative", "sham", "presentation", "bypass", "control")
# Every key a frame may have: one misspelt is refused, never silently ignored.
KEYS = {
    "name",
    *SITUATION,
    "baseline",
    "body",
    "anchors",
    "inputs",
    "observe",
    "interventions",
    "allowed",
    "standing",
    "battery",
    "materialized",
    "outsideScope",
}


class FrameError(ValueError):
    """A frame that cannot be assessed as declared."""


@dataclass(frozen=True)
class Span:
    """One piece of the body at the frame's grain."""

    id: str
    text: str
    kind: str = "text"


@dataclass(frozen=True)
class Frame:
    """A checked frame. It keeps the canonical JSON its hash is taken of, and
    every coordinate read from it is a fresh copy: nothing a battery or the
    caller does with what it reads can change what the hash names."""

    source: str
    hash: str
    spans: tuple[Span, ...]
    anchors: tuple[str, ...]
    labels: tuple[str, ...]
    quorum: int
    agree: int

    @property
    def raw(self) -> dict[str, Any]:
        return json.loads(self.source)

    @property
    def name(self) -> str:
        return self.raw["name"]

    @property
    def inputs(self) -> tuple[dict[str, str], ...]:
        return tuple(self.raw["inputs"])

    @property
    def instruction(self) -> str:
        return self.raw["observe"]["instruction"]

    @property
    def interventions(self) -> dict[str, Any]:
        return self.raw["interventions"]

    @property
    def allowed(self) -> dict[str, Any]:
        return self.raw["allowed"]

    @property
    def battery(self) -> dict[str, Any]:
        return self.raw["battery"]

    @property
    def outside_scope(self) -> str | None:
        return self.raw.get("outsideScope")


def canonical(value: Any) -> str:
    """The one serialization a hash is taken of."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load(path: str | Path) -> Frame:
    return parse(json.loads(Path(path).read_text(encoding="utf-8")))


def parse(raw: dict[str, Any]) -> Frame:
    """Check a frame and hash it. The frame keeps its own copy: changing the
    caller's dict afterwards cannot change what the hash names."""
    if not isinstance(raw, dict):
        raise FrameError("a frame is a JSON object")
    raw = copy.deepcopy(raw)

    def need(key: str, kind: type, where: dict[str, Any] = raw) -> Any:
        if key not in where:
            raise FrameError(f"the frame does not say its {key}")
        value = where[key]
        if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
            raise FrameError(f"{key} must be a {kind.__name__}")
        return value

    unknown = set(raw) - KEYS
    if unknown:
        raise FrameError(f"unknown keys: {sorted(unknown)}")
    need("name", str)
    for key in SITUATION:
        if not need(key, str).strip():
            raise FrameError(f"{key} is empty")
    if "baseline" not in raw:
        raise FrameError("the frame does not say its baseline (B0: what is pinned)")
    if not (isinstance(raw["baseline"], str | dict) and raw["baseline"]):
        raise FrameError("the baseline is a non-empty text or object")
    if not isinstance(raw.get("materialized", False), bool):
        raise FrameError("materialized is true or false")
    scope = raw.get("outsideScope")
    if scope is not None and not (isinstance(scope, str) and scope.strip()):
        raise FrameError("outsideScope is the receiving owner's exclusion, in words")

    body = need("body", dict)
    spans = tuple(_span(span) for span in need("spans", list, body))
    ids = [span.id for span in spans]
    if len(set(ids)) != len(ids):
        raise FrameError("two spans share an id")

    anchors = tuple(need("anchors", list))
    if not anchors:
        raise FrameError("a relation rests on at least one anchor")
    missing = [anchor for anchor in anchors if anchor not in ids]
    if missing:
        raise FrameError(f"anchors not in the body: {missing}")

    inputs = tuple(need("inputs", list))
    if not inputs or not all(
        isinstance(x, dict) and all(isinstance(x.get(k), str) and x[k] for k in ("id", "text"))
        for x in inputs
    ):
        raise FrameError("inputs are a non-empty list of {id, text}, both non-empty strings")
    if len({x["id"] for x in inputs}) != len(inputs):
        raise FrameError("two inputs share an id")

    observe = need("observe", dict)
    labels = tuple(need("labels", list, observe))
    if len(labels) < 2:
        raise FrameError("the observation has at least two labels to tell apart")
    if not all(isinstance(label, str) and label for label in labels) or len(set(labels)) != len(
        labels
    ):
        raise FrameError("labels are distinct, non-empty strings")
    instruction = need("instruction", str, observe)
    if not instruction.strip():
        raise FrameError("the instruction is empty")

    interventions = need("interventions", dict)
    unknown = set(interventions) - set(INTERVENTIONS)
    if unknown:
        raise FrameError(f"unknown interventions: {sorted(unknown)}")
    if interventions.get("ablation") is not True:
        raise FrameError("required influence is tested by ablation: declare it (ablation: true)")
    _check_interventions(interventions, spans, anchors, inputs)

    allowed = need("allowed", dict)
    if set(allowed) != {"ablation"}:
        raise FrameError("allowed says which observations ablation may produce, and only that")
    order = observe.get("order")
    if order is not None and not (
        isinstance(order, list)
        and all(isinstance(label, str) for label in order)
        and sorted(order) == sorted(labels)
    ):
        raise FrameError("observe.order orders exactly the labels")
    for value in allowed.values():
        if value in ("lower", "higher"):
            if order is None:
                raise FrameError(f"allowed '{value}' needs observe.order")
        elif not (
            isinstance(value, list)
            and value
            and all(isinstance(label, str) and label in labels for label in value)
        ):
            raise FrameError(
                "allowed lists one or more of the frame's labels, or says lower or higher"
            )

    standing = need("standing", dict)
    if not set(standing) <= {"quorum", "agree", "stable"}:
        raise FrameError("standing says quorum, agree and, optionally, stable")
    quorum, agree = need("quorum", int, standing), need("agree", int, standing)
    if not 1 <= agree <= quorum:
        raise FrameError("agree is between 1 and quorum")
    if not isinstance(standing.get("stable", False), bool):
        raise FrameError("stable is true or false")
    if standing.get("stable") and not interventions.get("repeat"):
        raise FrameError("stable reads the baseline and repeat sessions together: declare repeat")

    battery = need("battery", dict)
    need("kind", str, battery)

    source = canonical(raw)
    return Frame(
        source=source,
        hash=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        spans=spans,
        anchors=anchors,
        labels=labels,
        quorum=quorum,
        agree=agree,
    )


def _span(value: Any) -> Span:
    if not isinstance(value, dict) or not {"id", "text"} <= set(value) <= {"id", "text", "kind"}:
        raise FrameError("a span is {id, text} with an optional kind")
    if not all(isinstance(value[key], str) and value[key] for key in value):
        raise FrameError("a span's id, text and kind are non-empty strings")
    return Span(**value)


def _check_interventions(
    interventions: dict[str, Any],
    spans: tuple[Span, ...],
    anchors: tuple[str, ...],
    inputs: tuple[dict[str, str], ...],
) -> None:
    """Each intervention in the one shape the plan reads, and each able to
    change what the scorer reads: a trial identical to another would settle
    its check without testing it."""
    from .interventions import rename

    ids = [span.id for span in spans]
    if not isinstance(interventions.get("repeat", False), bool):
        raise FrameError("repeat is true or false")
    for key in ("cumulative", "bypass", "control"):
        value = interventions.get(key)
        if value is None:
            continue
        if not isinstance(value, list) or not value:
            raise FrameError(f"{key} lists the spans it removes")
        for span_id in value:
            if span_id not in ids:
                raise FrameError(f"{key} names a span not in the body: {span_id}")
    for key in ("bypass", "control"):
        if set(interventions.get(key) or []) == set(anchors):
            raise FrameError(f"{key} removes exactly the anchors: it is the ablation again")
    if "cumulative" in interventions and set(interventions["cumulative"]) <= set(anchors):
        raise FrameError("cumulative adds no span to the anchors: it is the ablation again")
    sham = interventions.get("sham")
    if not (sham is None or isinstance(sham, bool)):
        draws = sham.get("draws") if isinstance(sham, dict) else None
        if set(sham if isinstance(sham, dict) else ()) != {"draws"} or not (
            isinstance(draws, int) and not isinstance(draws, bool) and draws >= 1
        ):
            raise FrameError("sham is true or {draws: n} with n at least 1")
    presentation = interventions.get("presentation")
    if presentation is not None and not (
        isinstance(presentation, dict)
        and presentation
        and all(
            isinstance(k, str) and k and isinstance(v, str) and v for k, v in presentation.items()
        )
    ):
        raise FrameError("presentation maps words to their replacements")
    if presentation:
        if len({word.lower() for word in presentation}) != len(presentation):
            raise FrameError("presentation names a word twice (it renames without case)")
        mapping = tuple(sorted(presentation.items()))
        body_moves = any(rename(span.text, mapping) != span.text for span in spans)
        for x in inputs:
            if not body_moves and rename(x["text"], mapping) == x["text"]:
                raise FrameError(f"presentation renames nothing {x['id']} reads")
