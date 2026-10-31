"""MkDocs hook: the reference page names each module in an HTML comment.

GitHub hides `<!-- ::: gadfly.pipeline -->`, so the page reads there as its
table of modules; the site unwraps it into the `::: gadfly.pipeline` line
mkdocstrings expands into the module's reference.
"""

import re

MODULE = re.compile(r"^<!-- (::: \S+) -->$", re.M)


def on_page_markdown(markdown, page, config, files):
    return MODULE.sub(r"\1", markdown)
