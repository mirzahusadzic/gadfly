"""MkDocs hook: render GitHub's math syntax on the docs site.

docs/load-bearing.md keeps the text exactly as GitHub renders it: display
math as $`...`$ in a centred div, inline math as $`...`$. Arithmatex reads
$$...$$ and $...$, so the delimiters are rewritten at build time and the
source stays as written.
"""

import re

DISPLAY = re.compile(r'<div align="center">\s*\$`(.+?)`\$\s*</div>', re.S)
INLINE = re.compile(r"\$`(.+?)`\$")


def on_page_markdown(markdown, page, config, files):
    markdown = DISPLAY.sub(lambda m: f"\n$$\n{m.group(1)}\n$$\n", markdown)
    return INLINE.sub(lambda m: f"${m.group(1)}$", markdown)
