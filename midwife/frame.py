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
import math
import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

# The situated relation L = (I, B, r, g, P, T, B0, C, p): each must be said
# (the body B and the baseline B0 are checked on their own).
SITUATION = ("relation", "locus", "role", "grain", "purpose", "trajectory", "crossing", "promise")
INTERVENTIONS = (
    "repeat",
    "ablation",
    "cumulative",
    "sham",
    "presentation",
    "placement",
    "inversion",
    "inputInversion",
    "bypass",
    "control",
)
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
    "carriage",
    "scopeCheck",
}
# The receiving owner's independent check of an outsideScope exclusion.
SCOPE_CHECK = {"owner", "statement", "source", "encounter"}
# How a category treats the checks its trials left open: under all-checks
# (the default) carried and cooled need theirs passed; under listed they are
# listed beside the category, as After the Poem's study reads them.
CARRIAGE = ("all-checks", "listed")


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


def _read_once(frame: Frame) -> dict[str, Any]:
    """The frame's text decoded once and kept with it, for Gadfly's own reading
    of many inputs; a caller reads `Frame.raw`, a fresh copy each time, since
    nothing must change what the hash names."""
    decoded = frame.__dict__.get("_decoded")
    if decoded is None:
        decoded = json.loads(frame.source)
        object.__setattr__(frame, "_decoded", decoded)
    return decoded


# The keys a frame may leave out; null is not leaving one out, since it hashes
# differently, so the parser refuses it as the schema does.
OPTIONAL = {
    "": ("materialized", "carriage", "outsideScope", "scopeCheck"),
    "observe": ("order",),
    "standing": ("stable",),
    "allowed": ("bypass", "inversion", "inputInversion"),
    "interventions": ("repeat", "cumulative", "sham", "presentation", "placement", "inversion",
                      "inputInversion", "bypass", "control"),
}  # fmt: skip


def _no_null_options(raw: dict[str, Any]) -> None:
    for section, keys in OPTIONAL.items():
        where = raw if not section else raw.get(section)
        if not isinstance(where, dict):
            continue
        for key in keys:
            if key in where and where[key] is None:
                named = f"{section}.{key}" if section else key
                raise FrameError(f"{named} is null: leave it out instead")


def canonical(value: Any) -> str:
    """The one serialization a hash is taken of."""
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def digest(value: Any) -> str:
    """The SHA-256 of a value's canonical serialization."""
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def schema() -> dict[str, Any]:
    """The frame's JSON Schema (draft 2020-12), for editors and authoring
    checks. It describes the shape; `parse` stays the authority on what only
    code can check (anchors in the body, trials that change something)."""
    return json.loads(files(__package__).joinpath("frame.schema.json").read_text("utf-8"))


def load(path: str | Path) -> Frame:
    """Read a frame from a JSON file, then check and hash it as `parse` does."""
    return parse(json.loads(Path(path).read_text(encoding="utf-8")))


def parse(raw: dict[str, Any]) -> Frame:
    """Check a frame and hash it. The frame keeps its own copy: changing the
    caller's dict afterwards cannot change what the hash names."""
    if not isinstance(raw, dict):
        raise FrameError("a frame is a JSON object")
    try:
        _plain_json(raw, "the frame")
    except RecursionError:  # deeper than any frame needs, and than Python reads
        raise FrameError("the frame nests deeper than a frame can") from None
    raw = copy.deepcopy(raw)
    _no_null_options(raw)

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
    if not need("name", str):
        raise FrameError("the name is empty")
    for key in SITUATION:
        if not need(key, str).strip():
            raise FrameError(f"{key} is empty")
    if "baseline" not in raw:
        raise FrameError("the frame does not say its baseline (B0: what is pinned)")
    if not (isinstance(raw["baseline"], str | dict) and raw["baseline"]):
        raise FrameError("the baseline is a non-empty text or object")
    if not isinstance(raw.get("materialized", False), bool):
        raise FrameError("materialized is true or false")
    if raw.get("carriage", CARRIAGE[0]) not in CARRIAGE:
        raise FrameError("carriage is all-checks or listed")
    check = raw.get("scopeCheck")
    if check is not None:
        if raw.get("outsideScope") is None:
            raise FrameError("scopeCheck checks an outsideScope exclusion: declare the exclusion")
        if not (
            isinstance(check, dict)
            and set(check) == SCOPE_CHECK
            and all(isinstance(v, str) and v.strip() for v in check.values())
        ):
            raise FrameError(
                "scopeCheck says who checked the exclusion (owner), what they found "
                "(statement), from what (source) and when (encounter)"
            )
    scope = raw.get("outsideScope")
    if scope is not None and not (isinstance(scope, str) and scope.strip()):
        raise FrameError("outsideScope is the receiving owner's exclusion, in words")

    body = need("body", dict)
    if set(body) - {"spans"}:
        raise FrameError("the body holds its spans and nothing else")
    spans = tuple(_span(span) for span in need("spans", list, body))
    ids = [span.id for span in spans]
    known = set(ids)  # looked up, not scanned
    if len(set(ids)) != len(ids):
        raise FrameError("two spans share an id")

    anchors = tuple(need("anchors", list))
    if not anchors:
        raise FrameError("a relation rests on at least one anchor")
    missing = [anchor for anchor in anchors if anchor not in known]
    if missing:
        raise FrameError(f"anchors not in the body: {missing}")
    if len(set(anchors)) != len(anchors):
        raise FrameError("anchors name a span twice")

    inputs = tuple(need("inputs", list))
    if not inputs or not all(
        isinstance(x, dict) and all(isinstance(x.get(k), str) and x[k] for k in ("id", "text"))
        for x in inputs
    ):
        raise FrameError("inputs are a non-empty list of {id, text}, both non-empty strings")
    if any(set(x) != {"id", "text"} for x in inputs):
        raise FrameError("an input is its id and its text, and nothing else")
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
    if "ablation" not in allowed or not set(allowed) <= {
        "ablation",
        "bypass",
        "inversion",
        "inputInversion",
    }:
        raise FrameError(
            "allowed says what ablation may produce and, optionally, the opening bypass exposes"
            " and what an inversion or input inversion must reach"
        )
    if "bypass" in allowed and not interventions.get("bypass"):
        raise FrameError("allowed.bypass needs a bypass trial")
    if ("inversion" in allowed) != bool(interventions.get("inversion")):
        raise FrameError(
            "an inversion trial and allowed.inversion, what it must reach, go together"
        )
    if ("inputInversion" in allowed) != bool(interventions.get("inputInversion")):
        raise FrameError(
            "an input inversion and allowed.inputInversion, what it must reach, go together"
        )
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
        elif isinstance(value, list) and len(set(value)) != len(value):
            raise FrameError("allowed names a label twice")

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
    if not need("kind", str, battery):
        raise FrameError("battery.kind is empty")

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


def _plain_json(value: Any, where: str) -> None:
    """Refuse what JSON cannot carry: a hash must name a frame any strict JSON
    reader can read back (no NaN or infinity, no sets, no lone surrogates, only
    string keys)."""
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise FrameError(f"{where} is plain JSON: the key {key!r} is not a string")
            _plain_json(key, where)
            _plain_json(item, f"{where}.{key}")
    elif isinstance(value, list):
        for item in value:
            _plain_json(item, where)
    elif isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise FrameError(f"{where} is plain JSON: a string is not valid Unicode") from None
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise FrameError(f"{where} is plain JSON: {value} is not a JSON number")
    elif not (value is None or isinstance(value, bool | int)):
        raise FrameError(f"{where} is plain JSON: a {type(value).__name__} is not a JSON value")


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
    from .interventions import renamer

    ids = [span.id for span in spans]
    known = set(ids)  # looked up, not scanned
    if not isinstance(interventions.get("repeat", False), bool):
        raise FrameError("repeat is true or false")
    for key in ("cumulative", "bypass", "control"):
        value = interventions.get(key)
        if value is None:
            continue
        if not isinstance(value, list) or not value:
            raise FrameError(f"{key} lists the spans it removes")
        for span_id in value:
            if span_id not in known:
                raise FrameError(f"{key} names a span not in the body: {span_id}")
        if len(set(value)) != len(value):
            raise FrameError(f"{key} names a span twice")
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
    placement = interventions.get("placement")
    if placement is not None:
        from .interventions import place

        if not (isinstance(placement, dict) and set(placement) == {"span", "after"}):
            raise FrameError('placement moves one span after another: {"span": id, "after": id}')
        for span_id in placement.values():
            if span_id not in known:
                raise FrameError(f"placement names a span not in the body: {span_id}")
        if placement["span"] == placement["after"]:
            raise FrameError("placement moves a span after another span, not itself")
        if place(spans, placement["span"], placement["after"]) == spans:
            raise FrameError(
                f"placement leaves the order as it is: {placement['span']} already follows "
                f"{placement['after']}"
            )
    if presentation:
        if len({word.lower() for word in presentation}) != len(presentation):
            raise FrameError("presentation names a word twice (it renames without case)")
        renaming = renamer(tuple(sorted(presentation.items())))  # built once
        body_moves = any(renaming(span.text) != span.text for span in spans)
        for x in inputs:
            if not body_moves and renaming(x["text"]) == x["text"]:
                raise FrameError(f"presentation renames nothing {x['id']} reads")
    inversion = interventions.get("inversion")
    if inversion is not None:
        if not (
            isinstance(inversion, dict)
            and inversion
            and all(
                isinstance(k, str) and k and isinstance(v, str) and v for k, v in inversion.items()
            )
        ):
            raise FrameError("inversion maps phrases to their inversions")
        if len({phrase.lower() for phrase in inversion}) != len(inversion):
            raise FrameError("inversion names a phrase twice (it inverts without case)")
        # An inversion is the relation's own: each phrase is in an anchor, and
        # in no other span, so the trial changes the relation's sense alone.
        anchored = set(anchors)
        for phrase in inversion:
            found = re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE)
            if not any(found.search(span.text) for span in spans if span.id in anchored):
                raise FrameError(f"inversion's '{phrase}' is in no anchor")
            elsewhere = [s.id for s in spans if s.id not in anchored and found.search(s.text)]
            if elsewhere:
                raise FrameError(
                    f"inversion's '{phrase}' is also in {elsewhere[0]}, which is not an anchor"
                )
    asked = interventions.get("inputInversion")
    if asked is not None:
        if not (
            isinstance(asked, dict)
            and asked
            and all(isinstance(k, str) and k and isinstance(v, str) and v for k, v in asked.items())
        ):
            raise FrameError("inputInversion maps phrases of the input to their inversions")
        if len({phrase.lower() for phrase in asked}) != len(asked):
            raise FrameError("inputInversion names a phrase twice (it inverts without case)")
        # It turns what is asked, never the evidence: each phrase is in an input.
        for phrase in asked:
            found = re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE)
            if not any(found.search(x["text"]) for x in inputs):
                raise FrameError(f"inputInversion's '{phrase}' is in no input")
