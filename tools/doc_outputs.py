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

A module's reference sits between `<!-- api MODULE -->` and `<!-- end api -->`:
its docstring, then each public function and class in source order, with its
signature as the source writes it and its docstring, and beneath a class its
properties, listed with their types, and its public methods.

    uv run python tools/doc_outputs.py          # report each one that differs
    uv run python tools/doc_outputs.py --write  # rewrite them from the code and the sources
"""

from __future__ import annotations

import ast
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
API = re.compile(r"<!-- api (\S+) -->\n(.*?)<!-- end api -->", re.S)


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


def apis(page: str) -> list[Copy]:
    """Every module reference in a page, its module as the source."""
    text = (ROOT / page).read_text(encoding="utf-8")
    return [
        Copy(page, match.group(1), match.group(2), match.start(2), match.end(2))
        for match in API.finditer(text)
    ]


def _text(text: str) -> str:
    # an angle bracket outside code is text, not a tag
    parts = re.split(r"(`[^`]*`)", text)
    return "".join(p if p.startswith("`") else p.replace("<", "&lt;") for p in parts)


def _language(code: str) -> str:
    first = code.lstrip()
    return "bash" if first.startswith("uv ") else "json" if first.startswith('"') else "python"


def _prose(doc: str | None) -> str:
    """A docstring as Markdown: its indented examples fenced, in their language."""
    if not doc:
        return ""
    out, code = [], []
    for line in [*doc.splitlines(), ""]:
        if line.startswith("    ") and (code or not out or not out[-1].strip()):
            code.append(line[4:])
            continue
        if code:
            out += [f"```{_language(code[0])}", *code, "```"]
            code = []
        out.append(_text(line))
    return "\n".join(out).rstrip() + "\n"


FUNCTION = (ast.FunctionDef, ast.AsyncFunctionDef)


def _param(arg: ast.arg, default: ast.expr | None, source: str) -> str:
    return arg.arg if default is None else f"{arg.arg}={ast.get_source_segment(source, default)}"


def _property(fn: ast.FunctionDef | ast.AsyncFunctionDef, source: str) -> bool:
    return any(ast.get_source_segment(source, d) == "property" for d in fn.decorator_list)


def _signature(fn: ast.FunctionDef | ast.AsyncFunctionDef, source: str, method: bool) -> str:
    args = fn.args
    positional = args.posonlyargs + args.args
    defaults = [None] * (len(positional) - len(args.defaults)) + args.defaults
    params = []
    for i, (arg, default) in enumerate(zip(positional, defaults, strict=True)):
        if not (method and i == 0 and arg.arg in ("self", "cls")):
            params.append(_param(arg, default, source))
        if args.posonlyargs and arg is args.posonlyargs[-1]:
            params.append("/")
    if args.vararg:
        params.append(f"*{args.vararg.arg}")
    elif args.kwonlyargs:
        params.append("*")
    for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        params.append(_param(arg, default, source))
    if args.kwarg:
        params.append(f"**{args.kwarg.arg}")
    line = f"{fn.name}({', '.join(params)})"
    if len(line) <= 60:
        return line
    # a long signature takes a line per parameter, as a formatter writes it
    return "\n".join([f"{fn.name}(", *(f"    {p}," for p in params), ")"])


def _fenced(code: str) -> str:
    return f"```python\n{code}\n```\n"


def _public(node: ast.stmt) -> bool:
    return isinstance(node, (*FUNCTION, ast.ClassDef)) and not node.name.startswith("_")


def _attribute(fn: ast.FunctionDef | ast.AsyncFunctionDef, source: str) -> str:
    # a property is a value, not a call: its name, its type, its docstring's lead
    kind = ast.get_source_segment(source, fn.returns) if fn.returns else ""
    lead = (ast.get_docstring(fn) or "").partition("\n\n")[0].replace("\n", " ")
    said = ". ".join(part for part in (f"`{kind}`" if kind else "", _text(lead)) if part)
    return f"- **`{fn.name}`:** {said}\n"


def _entry(heading: str, code: str, doc: str | None) -> list[str]:
    # what it does, then how it is called, then the rest of its docstring
    lead, _, rest = (doc or "").partition("\n\n")
    return [heading, _prose(lead), _fenced(code), _prose(rest)]


def documented(module: str) -> str:
    """The reference text for `module`, from its source: a section under a
    rule, an entry for each public function and class, its methods beneath."""
    source = (ROOT / (module.replace(".", "/") + ".py")).read_text(encoding="utf-8")
    tree = ast.parse(source)
    parts = ["---\n", f"### {module}\n", _prose(ast.get_docstring(tree))]
    for node in filter(_public, tree.body):
        if isinstance(node, FUNCTION):
            signature = _signature(node, source, method=False)
            parts += _entry(f"#### {node.name}\n", signature, ast.get_docstring(node))
            continue
        bases = ", ".join(ast.get_source_segment(source, b) for b in node.bases)
        head = [f"@{ast.get_source_segment(source, d)}" for d in node.decorator_list]
        head.append(f"class {node.name}" + (f"({bases})" if bases else ""))
        parts += _entry(f"#### {node.name}\n", "\n".join(head), ast.get_docstring(node))
        members = [item for item in filter(_public, node.body) if isinstance(item, FUNCTION)]
        properties = [item for item in members if _property(item, source)]
        if properties:
            parts.append(f"{node.name} has these properties:\n")
            parts.append("".join(_attribute(item, source) for item in properties))
        for item in members:
            if not _property(item, source):
                signature = _signature(item, source, method=True)
                heading = f"##### {node.name}.{item.name}\n"
                parts += _entry(heading, signature, ast.get_docstring(item))
    # a blank line first, so no reader takes the rule for an underline
    return "\n" + "\n".join(part for part in parts if part)


def main(write: bool) -> int:
    differ = 0
    for page in PAGES:
        text = (ROOT / page).read_text(encoding="utf-8")
        found = [
            *((t, printed, " && ".join(t.commands)) for t in transcripts(page)),
            *((c, lambda c: copied(c.source), f"copy of {c.source}") for c in copies(page)),
            *((a, lambda a: documented(a.source), f"reference of {a.source}") for a in apis(page)),
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
    print(f"{differ} transcript(s), copies or references {'rewritten' if write else 'differ'}")
    return 0 if write or not differ else 1


if __name__ == "__main__":
    raise SystemExit(main("--write" in sys.argv))
