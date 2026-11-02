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
# Python's own, said by the command line: a file it cannot use, or Ctrl-C;
# and the exit itself
PYTHONS = {"FileExistsError", "FileNotFoundError", "PermissionError", "KeyboardInterrupt"}
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
            target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            if isinstance(node.exc, ast.Call) or target.id[0].isupper():
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


def test_a_refusal_says_what_went_wrong_and_its_notes_what_to_do():
    error = RecordsError("a record belongs to another frame", "read them with their own frame")
    assert str(error) == "a record belongs to another frame"
    assert error.__notes__ == ["read them with their own frame"]


def test_a_battery_that_refuses_with_a_value_error_is_a_battery_error(raw):
    class Picky:
        name = raw["battery"]["kind"]

        def check(self, frame):
            raise ValueError("this battery serves no refunds")  # as the protocol says

        def observe(self, frame, prompt, max_output_tokens):
            raise AssertionError("never asked")

    framed = situate(raw)
    with pytest.raises(BatteryError, match="serves no refunds"):
        run(framed, Picky(), Budget(calls=calls_needed(framed)))
