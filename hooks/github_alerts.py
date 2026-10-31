"""MkDocs hook: render GitHub's alerts as Material's admonitions.

The pages are written to read on GitHub, so a callout is a GitHub alert, and
its title, when it has one, is the bold line that opens it:

    > [!NOTE]
    > **Predicted before the first call**
    >
    > The ablation stays at request-changes.

The site shows the same callout as an admonition with that title; the source
stays as written.
"""

import re

KINDS = {
    "NOTE": "note",
    "TIP": "tip",
    "IMPORTANT": "abstract",
    "WARNING": "warning",
    "CAUTION": "danger",
}
ALERT = re.compile(r"^> \[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\][ \t]*\n((?:>.*(?:\n|$))*)", re.M)
TITLE = re.compile(r"\*\*(.+)\*\*")


def admonition(match: re.Match) -> str:
    lines = [line[2:] if line.startswith("> ") else line[1:] for line in match[2].splitlines()]
    title = ""
    if lines and (bold := TITLE.fullmatch(lines[0].strip())):
        title = f' "{bold[1]}"'
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines.pop(0)
    body = "\n".join(f"    {line}" if line.strip() else "" for line in lines)
    return f"!!! {KINDS[match[1]]}{title}\n\n{body}\n"


def on_page_markdown(markdown, page, config, files):
    return ALERT.sub(admonition, markdown)
