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

from .errors import FrameError, is_plain, plain, quoted

# The situated relation L = (I, B, r, g, P, T, B0, C, p): each must be said
# (the body B and the baseline B0 are checked on their own).
SITUATION = ("relation", "locus", "role", "grain", "purpose", "trajectory", "crossing", "promise")
INTERVENTIONS = (
    "repeat",
    "ablation",
    "eachAnchor",
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
    "holes",
    "offers",
}
# A hole is an anchor the body is missing, by id and kind: what a piece found
# further down a chain of frames must be to fill it (`midwife.recoil`).
HOLE_KEYS = {"id", "kind"}
# The receiving owner's independent check of an outsideScope exclusion.
SCOPE_CHECK = {"owner", "statement", "source", "encounter"}
# How a category treats the checks its trials left open: under all-checks
# (the default) carried and cooled need theirs passed; under listed they are
# listed beside the category, as After the Poem's study reads them.
CARRIAGE = ("all-checks", "listed")
# A span names its id and text, and may name its kind and the source it crossed from
SPAN_KEYS = {"id", "text", "kind", "source"}


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

    @property
    def holes(self) -> tuple[dict[str, str], ...]:
        return tuple(self.raw.get("holes", ()))

    @property
    def offers(self) -> str | None:
        return self.raw.get("offers")


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
    "": ("materialized", "carriage", "outsideScope", "scopeCheck", "holes", "offers"),
    "observe": ("order",),
    "standing": ("stable",),
    "allowed": ("bypass", "inversion", "inputInversion"),
    "interventions": ("repeat", "eachAnchor", "cumulative", "sham", "presentation", "placement",
                      "inversion", "inputInversion", "bypass", "control"),
}  # fmt: skip


def _no_null_options(raw: dict[str, Any]) -> None:
    for section, keys in OPTIONAL.items():
        where = raw if not section else raw.get(section)
        if not isinstance(where, dict):
            continue
        for key in keys:
            if key in where and where[key] is None:
                named = f"{section}.{key}" if section else key
                raise FrameError(f"key {named!r} is null", "leave it out instead")


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
        raw = copy.deepcopy(raw)  # its own copy, which recurses deeper than the check
    except RecursionError:  # deeper than any frame needs, and than Python reads
        raise FrameError("the frame nests deeper than a frame can") from None
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
        raise FrameError(f"unknown keys {quoted(sorted(unknown))}")
    if not need("name", str):
        raise FrameError("the name is empty")
    _one_name(raw["name"], "the name")
    for key in SITUATION:
        if not need(key, str).strip():
            raise FrameError(f"{key} is empty")
    if "baseline" not in raw:
        raise FrameError(
            "the frame does not say its baseline", "say under baseline what stays pinned"
        )
    if not (isinstance(raw["baseline"], str | dict) and raw["baseline"]):
        raise FrameError("the baseline is a non-empty text or object")
    if not isinstance(raw.get("materialized", False), bool):
        raise FrameError("materialized is true or false")
    if raw.get("carriage", CARRIAGE[0]) not in CARRIAGE:
        raise FrameError("carriage is all-checks or listed")
    check = raw.get("scopeCheck")
    if check is not None:
        if raw.get("outsideScope") is None:
            raise FrameError(
                "scopeCheck checks an outsideScope exclusion, and none is declared",
                "declare the exclusion under outsideScope",
            )
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
    for span_id in ids:
        _one_name(span_id, "span id")
    _check_holes(raw, known)

    anchors = tuple(need("anchors", list))
    if not anchors and not raw.get("holes"):  # holes stand in while a piece is awaited
        raise FrameError("a relation rests on at least one anchor")
    missing = [anchor for anchor in anchors if anchor not in known]
    if missing:
        raise FrameError(
            f"the body has no span {quoted(missing)}", "anchors name spans of the body"
        )
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
    for x in inputs:
        _one_name(x["id"], "input id")

    observe = need("observe", dict)
    labels = tuple(need("labels", list, observe))
    if len(labels) < 2:
        raise FrameError("the observation has at least two labels to tell apart")
    if not all(isinstance(label, str) and label for label in labels) or len(set(labels)) != len(
        labels
    ):
        raise FrameError("labels are distinct, non-empty strings")
    for label in labels:
        _one_name(label, "label")
    instruction = need("instruction", str, observe)
    if not instruction.strip():
        raise FrameError("the instruction is empty")

    interventions = need("interventions", dict)
    unknown = set(interventions) - set(INTERVENTIONS)
    if unknown:
        raise FrameError(f"unknown interventions {quoted(sorted(unknown))}")
    if interventions.get("ablation") is not True:
        raise FrameError(
            "required influence is tested by ablation, and none is declared", "set ablation to true"
        )
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
                raise FrameError(f"allowed {value!r} needs observe.order")
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
        raise FrameError(
            "stable reads the baseline and repeat sessions together, and no repeat is declared",
            "declare repeat",
        )

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
                raise FrameError(f"{where} is not plain JSON, as the key {key!r} is not a string")
            _plain_json(key, where)
            _plain_json(item, f"{where}.{plain(key)}")
    elif isinstance(value, list):
        for item in value:
            _plain_json(item, where)
    elif isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise FrameError(
                f"{where} is not plain JSON, as a string is not valid Unicode"
            ) from None
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise FrameError(f"{where} is not plain JSON, as {value!r} is not a JSON number")
    elif isinstance(value, int) and not isinstance(value, bool):
        try:
            str(value)
        except ValueError:  # past Python's limit on digits: no hash could hold it
            raise FrameError(
                f"{where} is not plain JSON, as a number is too long to write"
            ) from None
    elif not (value is None or isinstance(value, bool)):
        raise FrameError(
            f"{where} is not plain JSON, as a {type(value).__name__} is not a JSON value"
        )


def _one_name(value: str, what: str) -> None:
    """A name Gadfly prints where a reader, a script or another model reads
    lines: one line, with no colon a label would end at."""
    if not is_plain(value):
        raise FrameError(
            f"{what} {value!r} is not one plain name",
            "a name holds no line break and no colon followed by a space",
        )


def _check_holes(raw: dict[str, Any], known: set[str]) -> None:
    """A frame's holes, each an id and a kind, plain names, none a span the
    body already has; and the kind its decision climbs as, under `offers`."""
    holes = raw.get("holes")
    if holes is not None:
        if not (
            isinstance(holes, list)
            and holes
            and all(
                isinstance(hole, dict)
                and set(hole) == HOLE_KEYS
                and all(isinstance(value, str) and value for value in hole.values())
                for hole in holes
            )
        ):
            raise FrameError("holes lists what the body is missing, each an id and a kind")
        for hole in holes:
            _one_name(hole["id"], "hole id")
            _one_name(hole["kind"], "hole kind")
        ids = [hole["id"] for hole in holes]
        if len(set(ids)) != len(ids):
            raise FrameError("two holes share an id")
        taken = sorted(set(ids) & known)
        if taken:
            raise FrameError(
                f"holes name span {quoted(taken)}, which the body has",
                "a hole is what the body lacks",
            )
    offers = raw.get("offers")
    if offers is not None:
        if not (isinstance(offers, str) and offers):
            raise FrameError("offers names the kind the frame's decision climbs as")
        _one_name(offers, "offers")


def _span(value: Any) -> Span:
    if not isinstance(value, dict) or not {"id", "text"} <= set(value) <= SPAN_KEYS:
        raise FrameError("a span is {id, text} with an optional kind and source")
    named = {key: value[key] for key in ("id", "text", "kind") if key in value}
    if not all(isinstance(item, str) and item for item in named.values()):
        raise FrameError("a span's id, text and kind are non-empty strings")
    if "source" in value:
        _check_source(named["id"], named["text"], value["source"])
    return Span(**named)


def _check_source(span: str, text: str, source: Any) -> None:
    """A span that crossed from elsewhere names the SHA-256 of the exact text
    that crossed, and optionally where it came from: its text must hash to
    it, byte for byte, so what reached this frame is what left the other."""
    if not (
        isinstance(source, dict)
        and {"sha256"} <= set(source) <= {"sha256", "from"}
        and isinstance(source["sha256"], str)
        and re.fullmatch(r"[0-9a-f]{64}", source["sha256"])
        and ("from" not in source or (isinstance(source["from"], str) and source["from"]))
    ):
        raise FrameError(
            f"span {span!r} names a source that is not {{sha256, from}}",
            "sha256 is 64 lowercase hex digits; from, if given, says where the text came from",
        )
    found = hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()
    if found != source["sha256"]:
        raise FrameError(
            f"span {span!r} does not hash to its source",
            f"its text hashes to {found!r}; it must be byte for byte the text that crossed",
        )


def _check_sham_kind(pools: Any, spans: tuple[Span, ...], anchors: tuple[str, ...]) -> None:
    """A sham's `kind`, when given: anchors mapped to the kind of span their
    shams are drawn from instead of their own, each a kind the body has."""
    if pools is None:
        return
    if not (
        isinstance(pools, dict)
        and pools
        and all(isinstance(k, str) and isinstance(v, str) and v for k, v in pools.items())
    ):
        raise FrameError("sham kind maps anchors to the kind their shams are drawn from")
    kinds = {span.id: span.kind for span in spans}
    for anchor, kind in pools.items():
        if anchor not in anchors:
            raise FrameError(f"sham kind names {anchor!r}, which is no anchor")
        if kind not in kinds.values():
            raise FrameError(f"sham kind names kind {kind!r}, which no span has")
        if kind == kinds[anchor]:
            raise FrameError(
                f"sham kind maps {anchor!r} to its own kind, as shams are drawn anyway"
            )


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
                raise FrameError(f"{key} names span {span_id!r}, which is not in the body")
        if len(set(value)) != len(value):
            raise FrameError(f"{key} names a span twice")
    each = interventions.get("eachAnchor", False)
    if not isinstance(each, bool):
        raise FrameError("eachAnchor is true or false")
    if each and len(anchors) < 2:
        raise FrameError(
            "eachAnchor cuts each of several anchors alone, and one is the ablation again"
        )
    for key in ("bypass", "control"):
        if key in interventions and set(interventions[key] or []) == set(anchors):
            raise FrameError(f"{key} removes exactly the anchors, so it is the ablation again")
    if "cumulative" in interventions and set(interventions["cumulative"]) <= set(anchors):
        raise FrameError("cumulative adds no span to the anchors, so it is the ablation again")
    sham = interventions.get("sham")
    if not (sham is None or isinstance(sham, bool)):
        keys = set(sham) if isinstance(sham, dict) else set()
        draws = sham.get("draws") if isinstance(sham, dict) else None
        if not {"draws"} <= keys <= {"draws", "kind"} or not (
            isinstance(draws, int) and not isinstance(draws, bool) and draws >= 1
        ):
            raise FrameError(
                "sham is true, or a number of draws, at least 1, with an optional kind"
            )
        _check_sham_kind(sham.get("kind"), spans, anchors)
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
            raise FrameError(
                "placement moves one span after another", "name them as span and after"
            )
        for span_id in placement.values():
            if span_id not in known:
                raise FrameError(f"placement names span {span_id!r}, which is not in the body")
        if placement["span"] == placement["after"]:
            raise FrameError("placement moves a span after another span, not itself")
        if place(spans, placement["span"], placement["after"]) == spans:
            raise FrameError(
                f"placement leaves the order as it is, as {placement['span']!r} already follows "
                f"{placement['after']!r}"
            )
    if presentation:
        if len({word.lower() for word in presentation}) != len(presentation):
            raise FrameError("presentation names a word twice (it renames without case)")
        renaming = renamer(tuple(sorted(presentation.items())))  # built once
        body_moves = any(renaming(span.text) != span.text for span in spans)
        for x in inputs:
            if not body_moves and renaming(x["text"]) == x["text"]:
                raise FrameError(f"presentation renames nothing input {x['id']!r} reads")
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
                raise FrameError(f"inversion's {phrase!r} is in no anchor")
            elsewhere = [s.id for s in spans if s.id not in anchored and found.search(s.text)]
            if elsewhere:
                raise FrameError(
                    f"inversion's {phrase!r} is also in span {elsewhere[0]!r}, "
                    "which is not an anchor"
                )
        inverting = renamer(tuple(sorted(inversion.items())))
        if all(inverting(s.text) == s.text for s in spans if s.id in anchored):
            raise FrameError("inversion changes no anchor, as each phrase stays as it is")
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
                raise FrameError(f"inputInversion's {phrase!r} is in no input")
        turning = renamer(tuple(sorted(asked.items())))
        if all(turning(x["text"]) == x["text"] for x in inputs):
            raise FrameError("inputInversion changes no input, as each phrase stays as it is")
