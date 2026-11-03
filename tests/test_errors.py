"""What Gadfly refuses is a class for what the caller must fix, carrying its
exit status, as PEP 8, 352 and 678 shape Python's own errors."""

import ast
from pathlib import Path

import pytest

from midwife import errors, frame
from midwife.errors import BatteryError, FrameError, GadflyError, RecordsError, UsageError
from midwife.pipeline import calls_needed, run, situate
from midwife.types import Budget

ROOT = Path(__file__).parent.parent
REFUSALS = {"UsageError", "FrameError", "RecordsError", "BatteryError"}
WARNINGS = {"OpeningWarning", "StoppedWarning"}
# Python's own, said by the command line: a file it cannot use, or Ctrl-C;
# and the exit itself
PYTHONS = {"FileExistsError", "FileNotFoundError", "PermissionError", "KeyboardInterrupt"}
PYTHONS |= {"IsADirectoryError", "NotADirectoryError"}
PYTHONS |= {"SystemExit"}
# raised and caught inside a battery, never reaching its caller
INSIDE = {
    ("batteries/critic.py", "TimeoutError"),
    ("batteries/critic.py", "Late"),
    ("batteries/critic.py", "KeyError"),
    ("batteries/unified.py", "TimeoutError"),
}


def raised(path: Path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Raise) and node.exc is not None:
            exc = node.exc
            if isinstance(exc, ast.Call) and getattr(exc.func, "id", None) == "noted":
                exc = exc.args[0]  # Python's own error, with notes
            target = exc.func if isinstance(exc, ast.Call) else exc
            if isinstance(exc, ast.Call) or target.id[0].isupper():
                yield node.lineno, target.id if isinstance(target, ast.Name) else target.attr


def test_every_refusal_is_one_of_the_classes():
    stray = []
    for path in sorted((ROOT / "midwife").rglob("*.py")):
        where = str(path.relative_to(ROOT / "midwife"))
        for line, name in raised(path):
            # `refusal` is the class a loader is handed: one of REFUSALS
            if name not in REFUSALS | PYTHONS | {"refusal"} and (where, name) not in INSIDE:
                stray.append(f"{where}:{line} {name}")
    assert stray == []


def test_each_class_carries_its_exit_status_and_is_a_value_error():
    statuses = {UsageError: 2, FrameError: 4, RecordsError: 5, BatteryError: 6}
    assert {kind: kind.exit for kind in statuses} == statuses
    assert all(issubclass(kind, GadflyError) and issubclass(kind, ValueError) for kind in statuses)
    assert frame.FrameError is errors.FrameError  # where callers have always found it


def test_coverage_sees_midwife_from_its_first_line(midwife_imported_before):
    # pytest's own settings import nothing of midwife, so coverage, started
    # before tests/conftest.py, measures each module from its first line; the
    # warning filter that names a Gadfly class is set from the conftest
    assert midwife_imported_before is False


def test_a_refusal_says_what_went_wrong_and_its_notes_what_to_do():
    error = RecordsError("a record belongs to another frame", "read them with their own frame")
    assert str(error) == "a record belongs to another frame"
    assert error.__notes__ == ["read them with their own frame"]


def test_a_battery_that_refuses_with_a_value_error_is_a_battery_error(raw):
    class Picky:
        name = raw["battery"]["kind"]

        def check(self, frame):
            raise ValueError("this battery serves no refunds:\nnone")  # as the protocol says

        def observe(self, frame, prompt, max_output_tokens):
            raise AssertionError("never asked")

    framed = situate(raw)
    with pytest.raises(BatteryError) as refused:
        run(framed, Picky(), Budget(calls=calls_needed(framed)))
    # Gadfly's words in the message, the battery's own in a note
    assert str(refused.value) == f"battery {raw['battery']['kind']!r} refused this frame"
    assert refused.value.__notes__ == ["it said 'this battery serves no refunds:\\nnone'"]


def said(path: Path):
    # each refusal's own words: its message and its notes, as written
    source = path.read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            call = node.exc
            if getattr(call.func, "id", None) == "noted":  # Python's own error, with notes
                call, notes = call.args[0], call.args[1:]
                words = [*call.args, *notes] if isinstance(call, ast.Call) else notes
            else:
                words = call.args
            for word in words:
                yield (
                    node.lineno,
                    ast.get_source_segment(source, word),
                    "".join(
                        part.value
                        for part in ast.walk(word)
                        if isinstance(part, ast.Constant) and isinstance(part.value, str)
                    ),
                )


def test_a_message_and_its_notes_hold_no_colon_and_no_python_list():
    # `Type: message` has its one colon; a list prints as words, not ['r9']
    stray = []
    for path in sorted((ROOT / "midwife").rglob("*.py")):
        for line, source, words in said(path):
            listed = "join" in source or "quoted(" in source  # a list said as words
            if ": " in words or "sorted(" in source and not listed:
                stray.append(f"{path.relative_to(ROOT)}:{line} {source[:60]}")
    assert stray == []


def test_an_openings_reason_holds_no_colon():
    # run says it on one line: `openings: 3 of 8 calls, most often "<reason>" (3)`
    stray = []
    for path in sorted((ROOT / "midwife").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.keyword) and node.arg == "opening":
                words = "".join(
                    part.value
                    for part in ast.walk(node.value)
                    if isinstance(part, ast.Constant) and isinstance(part.value, str)
                )
                if ": " in words:
                    stray.append(f"{path.relative_to(ROOT)}:{node.value.lineno}")
    assert stray == []


# what a refusal or an opening may put in its words unquoted: Gadfly's own
# words, numbers, and Python's words in parentheses; any value a caller or a
# service supplied is quoted, as Python's own messages quote one
UNQUOTED = {
    "what", "where", "at", "key", "stopped", "self.prog", "line", "pin", "status_line",
    "error.msg", "error.code", "tried", "said", "MAX_TIMEOUT", "frame.quorum", "len(unread)",
    "type(reason).__name__", "type(error).__name__", "type(value).__name__", "kind.__name__",
    "many", "often", "made", "result.planned", "len(result.records)",
    "', '.join(EFFORTS)", "', '.join(wrong)", "max_output_tokens", "ANSWER_TOKENS", "MAX_ENDPOINTS",
    "side", "most", "each", "args.calls",
}  # fmt: skip


def worded(path: Path):
    # every message, note and opening reason, as written in the source
    source = path.read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            call = node.exc
            if getattr(call.func, "id", None) == "noted":
                yield from call.args[1:]
                call = call.args[0]
            if isinstance(call, ast.Call) and getattr(call.func, "id", "") in REFUSALS | PYTHONS:
                yield from call.args
            elif isinstance(call, ast.Call) and getattr(call.func, "id", "") == "refusal":
                yield from call.args
        elif isinstance(node, ast.Call) and getattr(node.func, "id", "") in WARNINGS:
            yield from node.args
        elif isinstance(node, ast.keyword) and node.arg == "opening":
            yield node.value
        elif isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "opening":
            yield node.value
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
            first = node.value.elts[0] if node.value.elts else None
            if (
                isinstance(first, ast.Constant)
                and first.value is None
                and len(node.value.elts) == 2
            ):
                yield node.value.elts[1]  # a battery's (no label, why) pair


def test_every_value_a_refusal_or_an_opening_names_is_quoted():
    stray = []
    for path in sorted((ROOT / "midwife").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        for words in worded(path):
            if isinstance(words, ast.Call) and getattr(words.func, "id", "") == "str":
                stray.append(f"{path.relative_to(ROOT)}:{words.lineno} str(...) unquoted")
            for part in ast.walk(words):
                if isinstance(part, ast.FormattedValue) and part.conversion != ord("r"):
                    value = ast.get_source_segment(source, part.value)
                    # quoted() and _named() quote what they are given
                    if value not in UNQUOTED and not value.startswith(("quoted(", "_named(")):
                        stray.append(f"{path.relative_to(ROOT)}:{part.lineno} {{{value}}}")
    assert stray == []


def test_a_run_says_what_it_did_not_do_as_asked_with_warnings(raw):
    # nothing passes in silence (PEP 20): openings and an early stop are warnings
    # (PEP 230), which a caller may make errors with Python's own filters
    import warnings

    from midwife.errors import GadflyWarning, OpeningWarning, StoppedWarning
    from tests.fixtures.refund import Unreachable

    raw["battery"] = {"kind": "rule-reader"}
    frame = situate(raw)
    n = calls_needed(frame)
    with pytest.warns(OpeningWarning, match=rf"^{n} of {n} calls came back as .* \({n} times\)$"):
        run(frame, Unreachable(), Budget(calls=n))
    with pytest.warns(StoppedWarning, match=rf"^the run stopped after 3 of {n} calls; the token"):
        run(frame, Unreachable(), Budget(calls=n, output_tokens_per_call=10, tokens=30))
    with warnings.catch_warnings():
        warnings.simplefilter("error", OpeningWarning)
        with pytest.raises(OpeningWarning):
            run(frame, Unreachable(), Budget(calls=calls_needed(frame)))
    assert (OpeningWarning.exit, StoppedWarning.exit) == (1, 3)
    assert issubclass(OpeningWarning, GadflyWarning) and issubclass(GadflyWarning, UserWarning)


def test_one_opening_is_said_once(raw):
    from midwife.errors import OpeningWarning
    from tests.fixtures.refund import RuleReader, Unreachable

    class OnceUnreachable(RuleReader):
        calls = 0

        def observe(self, frame, prompt, max_output_tokens):
            OnceUnreachable.calls += 1
            if OnceUnreachable.calls == 1:
                return Unreachable().observe(frame, prompt, max_output_tokens)
            return super().observe(frame, prompt, max_output_tokens)

    raw["battery"] = {"kind": "rule-reader"}
    frame = situate(raw)
    with pytest.warns(OpeningWarning, match=r"\(ConnectionRefused\)' once$"):
        run(frame, OnceUnreachable(), Budget(calls=calls_needed(frame)))
