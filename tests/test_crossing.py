"""Boundary crossings: a span that names the source it crossed from, and a
reading made through a maker at one grain and a reader at the next. No model
is called; the makers and readers are rules."""

import copy
import hashlib

import pytest

from midwife.errors import FrameError
from midwife.frame import parse
from tests.test_schema import VALIDATOR


def sourced(text, origin="the refund policy, version 3"):
    return {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "from": origin}


def test_a_span_that_crossed_names_the_exact_text_that_left(raw):
    plain = parse(copy.deepcopy(raw))
    text = raw["body"]["spans"][1]["text"]
    raw["body"]["spans"][1]["source"] = sourced(text)
    frame = parse(raw)
    assert VALIDATOR.is_valid(raw)
    assert frame.spans[1] == plain.spans[1]  # the reader gets the same text
    assert frame.hash != plain.hash  # the frame names where it came from, so it is another frame
    raw["body"]["spans"][1]["source"] = {"sha256": sourced(text)["sha256"]}  # from is optional
    parse(raw)


def test_a_span_whose_text_is_not_what_crossed_is_refused(raw):
    raw["body"]["spans"][1]["source"] = sourced("A refund requires a receipt, kept 30 days.")
    with pytest.raises(FrameError, match="span 'r2' does not hash to its source") as refused:
        parse(raw)
    found = hashlib.sha256(raw["body"]["spans"][1]["text"].encode()).hexdigest()
    assert refused.value.__notes__ == [
        f"its text hashes to {found!r}; it must be byte for byte the text that crossed"
    ]
    assert VALIDATOR.is_valid(raw)  # only the parser reads the text against its hash
    raw["body"]["spans"][1]["source"] = {"sha256": "0" * 64, "from": ""}
    with pytest.raises(FrameError, match="names a source that is not"):
        parse(raw)
