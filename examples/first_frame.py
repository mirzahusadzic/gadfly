"""The tutorial's frame (docs/first-frame.md), run: does an answer's crate
count rest on cited source S-2?

    python examples/first_frame.py
"""

import json
from pathlib import Path

from examples.citation import CitationReader
from gadfly.pipeline import calls_needed, judge, run, situate
from gadfly.types import Budget

frame = situate(json.loads(Path("examples/citation.json").read_text()))
kept = []
result = run(frame, CitationReader(), Budget(calls=calls_needed(frame)), on_record=kept.append)
[finding] = judge(frame, kept)
print(finding.category)
print(*finding.evidence, sep="\n")
for line in finding.obligations:  # what the trials did not settle
    print(line)
