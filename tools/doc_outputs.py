"""The outputs the docs quote are the outputs the code prints, and the text
they copy is the text it copies.

A ```text block that opens with `$ ` lines is a transcript: each `$` line
is run from the repository root, in order, and what the last one prints is
what the block must show below it. A `.jsonl` argument the repository does
not hold is a new records file, made in a fresh directory, so a transcript
never writes into the repository; one it holds is kept records, read in place.

A copy sits between `<!-- copy SOURCE -->` and `<!-- end copy -->`. SOURCE is
a file, fenced when it is not Markdown, or `README.md:NAME`, the README's text
between `<!-- start:NAME -->` and `<!-- end:NAME -->`. The pages hold the text
itself rather than an include, so each reads whole on GitHub too.

    uv run python tools/doc_outputs.py          # report each transcript or copy that differs
    uv run python tools/doc_outputs.py --write  # rewrite them from the code and the sources
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
COPY = re.compile(r"<!-- copy (\S+) -->\n(.*?)<!-- end copy -->", re.S)


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
                str(Path(scratch) / Path(arg).name)
                if arg.endswith(".jsonl") and not (ROOT / arg).exists()
                else arg
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


@dataclass(frozen=True)
class Copy:
    page: str
    source: str
    quoted: str
    start: int
    end: int

    def where(self) -> str:
        line = (ROOT / self.page).read_text(encoding="utf-8")[: self.start].count("\n") + 1
        return f"{self.page}:{line}"


def copies(page: str) -> list[Copy]:
    """Every copy in a page."""
    text = (ROOT / page).read_text(encoding="utf-8")
    return [
        Copy(page, match.group(1), match.group(2), match.start(2), match.end(2))
        for match in COPY.finditer(text)
    ]


def copied(source: str) -> str:
    """The text a copy of `source` holds."""
    path, _, name = source.partition(":")
    text = (ROOT / path).read_text(encoding="utf-8")
    if name:
        start, end = f"<!-- start:{name} -->\n", f"<!-- end:{name} -->"
        return text[text.index(start) + len(start) : text.index(end)]
    if path.endswith(".md"):
        return text
    return f"```{Path(path).suffix.lstrip('.')}\n{text}```\n"


def main(write: bool) -> int:
    differ = 0
    for page in PAGES:
        text = (ROOT / page).read_text(encoding="utf-8")
        found = [
            *((t, printed, " && ".join(t.commands)) for t in transcripts(page)),
            *((c, lambda c: copied(c.source), f"copy of {c.source}") for c in copies(page)),
        ]
        # from the end, so offsets hold
        for block, now, what in sorted(found, key=lambda f: f[0].start, reverse=True):
            output = now(block)
            if output != block.quoted:
                differ += 1
                print(f"{block.where()}: {what}")
                text = text[: block.start] + output + text[block.end :]
        if write and found:
            (ROOT / page).write_text(text, encoding="utf-8")
    print(f"{differ} transcript(s) or copies {'rewritten' if write else 'differ'}")
    return 0 if write or not differ else 1


if __name__ == "__main__":
    raise SystemExit(main("--write" in sys.argv))
