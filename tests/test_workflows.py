"""What the workflows promise: the site publishes only main's own pushes."""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_the_site_publishes_only_a_push_to_this_repositorys_main():
    # CI runs on pull requests too, and a workflow_run trigger filters on the
    # branch's name alone: a fork's branch named main must never publish, and
    # a manual run publishes main only
    pages = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    build = re.search(r"\n  build:\n(.*?)\n  deploy:", pages, re.S).group(1)
    gate = re.search(r"if: >-\n((?:      .*\n)+)", build).group(1)
    for condition in (
        "github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'",
        "github.event.workflow_run.conclusion == 'success'",
        "github.event.workflow_run.event == 'push'",
        "github.event.workflow_run.head_branch == 'main'",
        "github.event.workflow_run.head_repository.full_name == github.repository",
    ):
        assert condition in gate, condition
    assert "needs: build" in pages
