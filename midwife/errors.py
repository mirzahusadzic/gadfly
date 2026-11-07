"""What Gadfly refuses, as Python names it: a class for what the caller must
fix (PEP 8), its exit status an attribute of the class (PEP 352), a message
that says what went wrong, and notes that say what to do (PEP 678).

    UsageError     2  the command or the call: flags, budget, standard input
    FrameError     4  the frame
    RecordsError   5  records or a report that are not this frame's run
    BatteryError   6  the battery: its module, its settings, its service

A file the command line cannot read or write is Python's own error
(PEP 3151), exit 7. Each class is a ValueError, as every refusal was.

What a run did not do as asked, though it went on and kept its records, is
a warning (PEP 230), raised with `warnings.warn`, which a caller may make an
error with Python's own filters (`-W error::midwife.errors.OpeningWarning`):

    OpeningWarning  1  calls came back with no answer (1 when every one did)
    StoppedWarning  3  the run stopped before its plan's end
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable

# The statuses no GadflyError carries: Python's own file errors, Ctrl-C, and
# anything else raised, which is a bug (EX_SOFTWARE)
FILE, INTERRUPTED, BUG = 7, 130, 70
# a reader that stopped reading: SIGPIPE's in a shell, given by hand where
# there is no SIGPIPE (Windows)
PIPE = 141


class GadflyError(ValueError):
    """A refusal: the message says what went wrong, each note what to do."""

    exit = 2

    def __init__(self, message: str, *notes: str) -> None:
        super().__init__(message)
        for note in notes:
            self.add_note(note)


def one_line(value: str) -> bool:
    """Whether a value prints on one line: no line break, nor any other
    control character a terminal could act on."""
    return not any(unicodedata.category(c) in ("Cc", "Zl", "Zp") for c in value)


def is_plain(value: str) -> bool:
    """Whether a value prints as one plain name: no line break, and no colon a
    label would end at."""
    return ": " not in value and one_line(value)


def plain(value: str) -> str:
    """A value as a line prints it: as it is when it is one plain name, else
    quoted as Python's repr, so it can neither end a label nor start a line.
    A name that ends in a colon is quoted too: printed before a space, its
    colon would end a label."""
    return value if is_plain(value) and not value.endswith(":") else repr(value)


def quoted(values: Iterable[str]) -> str:
    """Values as a message names them: each quoted, as Python's repr does."""
    return ", ".join(map(repr, values))


def noted[E: BaseException](error: E, *notes: str) -> E:
    """Python's own `error`, with notes that say what to do: its constructor
    takes none."""
    for note in notes:
        error.add_note(note)
    return error


class UsageError(GadflyError):
    """The command or the call asks for what cannot be done: a flag, a
    budget, standard input."""

    exit = 2


class FrameError(GadflyError):
    """A frame that cannot be assessed as declared."""

    exit = 4


class RecordsError(GadflyError):
    """Records or a report that are not what this frame's run made."""

    exit = 5


class BatteryError(GadflyError):
    """A battery that cannot be made, cannot serve this frame as set up, or
    cannot reach what it needs."""

    exit = 6


class StopRun(Exception):  # noqa: N818 — a signal, not a failure to report
    """Raised by a battery or a maker when its harness, not the frame, has
    failed, so no further call can be read: a refused key, a broken tool.
    The run makes no record of that call and starts no other; calls already
    out end and are kept, and it ends as a stopped run that quotes `reason`,
    as a spent budget ends one, so `--kept` finishes it once the harness is
    fixed. Never a label, and never an opening."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = str(reason)


class GadflyWarning(UserWarning):
    """What a run did not do as asked, though it went on and kept its
    records."""

    exit = 0


class OpeningWarning(GadflyWarning):
    """Calls came back with no answer, as openings; exit 1 when every call did,
    as then nothing was read."""

    exit = 1


class StoppedWarning(GadflyWarning):
    """The run stopped before its plan's end, so its records are partial."""

    exit = 3
