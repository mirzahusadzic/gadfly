"""What Gadfly refuses, as Python names it: a class for what the caller must
fix (PEP 8), its exit status an attribute of the class (PEP 352), a message
that says what went wrong, and notes that say what to do (PEP 678).

    UsageError     2  the command or the call: flags, budget, standard input
    FrameError     4  the frame
    RecordsError   5  records or a report that are not this frame's run
    BatteryError   6  the battery: its module, its settings, its service

A file the command line cannot read or write is Python's own error
(PEP 3151), exit 7. Each class is a ValueError, as every refusal was.
"""

from __future__ import annotations

from collections.abc import Iterable

# The statuses no GadflyError carries: Python's own file errors, Ctrl-C, and
# anything else raised, which is a bug (EX_SOFTWARE)
FILE, INTERRUPTED, BUG = 7, 130, 70


class GadflyError(ValueError):
    """A refusal: the message says what went wrong, each note what to do."""

    exit = 2

    def __init__(self, message: str, *notes: str) -> None:
        super().__init__(message)
        for note in notes:
            self.add_note(note)


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
