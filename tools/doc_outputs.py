"""The outputs the docs quote are the outputs the code prints.

A ```text block that opens with `$ ` lines is a transcript: each `$` line
is run from the repository root, in order, and what the last one prints is
what the block must show below it. A `.jsonl` argument is a records file in
a fresh directory, so a transcript never writes into the repository.

    uv run python tools/doc_outputs.py          # report each transcript that differs
    uv run python tools/doc_outputs.py --write  # rewrite them from what the code prints
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["README.md", *sorted(str(p.relative_to(ROOT)) for p in ROOT.glob("docs/**/*.md"))]
BLOCK = re.compile(r"```text\n((?:\$ [^\n]*\n)+)(.*?)```", re.S)


@dataclass(frozen=True)
class Transcript:
    page: str
    commands: tuple[str, ...]
    quoted: str
    start: int
    end: int

    def where(self) -> str:
        line = (ROOT / self.page).read_text(encoding="utf-8")[: self.start].count("\n") + 1
        return f"{self.page}:{line}"


def transcripts(page: str) -> list[Transcript]:
    """Every transcript block in a page."""
    text = (ROOT / page).read_text(encoding="utf-8")
    return [
        Transcript(
            page,
            tuple(line[2:] for line in match.group(1).splitlines()),
            match.group(2),
            match.start(2),
            match.end(2),
        )
        for match in BLOCK.finditer(text)
    ]


def printed(transcript: Transcript) -> str:
    """What the transcript's last command prints, run as written from the root."""
    with tempfile.TemporaryDirectory() as scratch:
        env = {**os.environ, "PYTHONPATH": str(ROOT), "NO_COLOR": "1"}
        out = ""
        for command in transcript.commands:
            argv = [
                str(Path(scratch) / Path(arg).name) if arg.endswith(".jsonl") else arg
                for arg in shlex.split(command.replace("\\\n", " "))
            ]
            if argv[:2] == ["uv", "run"]:
                argv = argv[2:]
            if argv[0] == "python":
                argv[0] = sys.executable
            elif argv[0] == "gadfly":
                argv[:1] = [sys.executable, "-m", "gadfly"]
            done = subprocess.run(
                argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=120
            )
            out = (done.stdout + done.stderr).replace(scratch + os.sep, "")
        return out


def main(write: bool) -> int:
    differ = 0
    for page in PAGES:
        found = transcripts(page)
        text = (ROOT / page).read_text(encoding="utf-8")
        for transcript in reversed(found):  # from the end, so offsets hold
            output = printed(transcript)
            if output != transcript.quoted:
                differ += 1
                print(f"{transcript.where()}: {' && '.join(transcript.commands)}")
                text = text[: transcript.start] + output + text[transcript.end :]
        if write and found:
            (ROOT / page).write_text(text, encoding="utf-8")
    print(f"{differ} transcript(s) {'rewritten' if write else 'differ'}")
    return 0 if write or not differ else 1


if __name__ == "__main__":
    raise SystemExit(main("--write" in sys.argv))
