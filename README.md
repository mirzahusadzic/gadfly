# Gadfly

[![CI](https://github.com/mirzahusadzic/gadfly/actions/workflows/ci.yml/badge.svg)](https://github.com/mirzahusadzic/gadfly/actions/workflows/ci.yml)
[![midwife on PyPI](https://img.shields.io/github/v/tag/mirzahusadzic/gadfly?sort=semver&label=midwife&logo=pypi&logoColor=white)](https://pypi.org/project/midwife/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23962158.svg)](https://doi.org/10.5281/zenodo.23962158)

Gadfly tests whether a decision rests on the evidence you think it rests on.
It removes or changes one declared line under fixed interventions, has a
scorer read each trial, and reads one verdict by fixed rules. The method is
[When meaning is load-bearing](https://mirzahusadzic.github.io/gadfly/load-bearing).

- **Fixed rules, not a model:** a verdict follows from the kept answers, so
  anyone can check it.
- **It says what it does not know:** an unresolved verdict names the check
  still open, kept apart from the evidence.
- **Kept records:** every answer is tied to its exact frame, and reading a run
  back calls no model.
- **Small:** a Python 3.13 library with no runtime dependencies and no hidden
  state.

Use it when you can name the premise and a consequence that should change
without it: a changelog line, a contributing rule, a contract clause, an
access grant. For a score or a ranking, use an ordinary evaluation.

---

<!-- start:verdicts -->
### What Gadfly says

Each input gets one **finding**, and a frame with several inputs gets one
**overall** category over them. The categories are not scores; the first rule
that matches names the category.

- **`carried`:** ablation moved the observation as the promise allows, and
  every carriage check passed: presentation and the shams held, the bypass
  exposed its opening, and the frame says the observation is what the
  recipient receives.
- **`coupled but misaligned`:** the relation matters, but presentation or
  placement moved it, or ablation moved it where the promise disallows.
- **`cooled`:** ablation left the observation unchanged while a control
  showed the scorer can move, so this relation has no operative influence
  here.
- **`unresolved`:** there is not enough agreed evidence: a trial is missing
  or split, repeat is unstable, a sham moved too, the scorer cannot tell, or a
  check the category needs is still open.
- **`outside scope`:** the receiving owner declares the distinction
  unnecessary, and their own check of that exclusion is recorded.

Every finding keeps its **evidence** (why this category) apart from its
**obligations** (what the trials did not settle), and an obligation is not a
passed check.

Under the default `carriage: all-checks`, a category waits
for the checks it needs: carried for every carriage check, cooled for a
control that moved, outside scope for the owner's scope check. Until then
the finding is unresolved, and any other open check is listed beside the
category. A frame with `carriage: listed` names the category at once and
lists its open checks beside it.
<!-- end:verdicts -->

---

### Install

Gadfly is the `midwife` package on PyPI
([why](https://mirzahusadzic.github.io/gadfly/in-plain-words#why-a-gadfly-and-a-midwife)),
for Python 3.13 or later. Its command, `gadfly`, goes on your path with
[uv](https://docs.astral.sh/uv/) or pipx, and `uvx` runs it once without
installing it:

```bash
uv tool install midwife
gadfly --version
uvx --from midwife gadfly --help
```

To use it from Python, add it to your project with `uv add midwife` or
`pip install midwife`, then `import midwife`. The examples read records kept
in the repository, so to run them, clone it:

```bash
git clone https://github.com/mirzahusadzic/gadfly.git
cd gadfly
uv sync
```

Reading the kept examples back needs nothing more. A live run also needs a
battery: a scorer on this machine that Gadfly asks each trial.

#### Set up a battery

Each shipped battery calls a service on this machine: install and start
[eGemma](https://github.com/mirzahusadzic/egemma) for Gemma 4, or the [unified
model router](https://github.com/mirzahusadzic/unified-model-router) for Claude,
DeepSeek and the other models it serves.
[Batteries](https://mirzahusadzic.github.io/gadfly/batteries#addresses-and-keys)
has each one's address and key, the other shipped batteries, and your own.

---

### Use

Every example is a real experiment: a frame, the predictions written before
its first call, and the records of each run, read by Gemma 4 26B through
eGemma, or for rungs 19 to 22 by Muse Spark 1.3 Contributor through the
router, which in rung 20 also writes what it reads.
Reading one back calls no model:

```text
$ uv run python examples/read.py examples/07-sql-rule.json
sql-rule: 5 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         review
baseline      request-changes 25
repeat        request-changes 25
ablation      request-changes 25
sham-1        request-changes 25
sham-2        request-changes 25
presentation  request-changes 25
control       approve 25
run 1: cooled
run 2: cooled
run 3: cooled
run 4: cooled
run 5: cooled
```

A pull request formats a value into SQL, which the repository's rules forbid.
Gemma asks for changes with the rule and without it, so its training decides
and the rule carries nothing here: `cooled`. [Your first
frame](https://mirzahusadzic.github.io/gadfly/first-frame) climbs one frame, a trial at a time, to `carried`.

#### Run a frame

With a battery set up, these four commands check a frame, show its trials
and their cost, run it, and read its verdict:

```bash
uv run gadfly check-frame examples/upgrade.json
uv run gadfly plan examples/upgrade.json
uv run gadfly run examples/upgrade.json \
  --battery midwife.batteries.egemma:EGemma \
  --calls 40 --out records.jsonl
uv run gadfly report examples/upgrade.json records.jsonl
```

`check-frame` and `plan` make no call, and `run` keeps each record as one JSON
line the moment it exists. [Command line](https://mirzahusadzic.github.io/gadfly/command-line) has every
command and flag, `stats` and recoil's `walk`, `successor`, `firm` and `gate`
among them.

#### From Python

The same test in Python reads a kept run back, then makes a fresh one:

<!-- start:use -->
```python
import json
from pathlib import Path

from midwife.batteries.egemma import EGemma
from midwife.cli import load_records
from midwife.pipeline import calls_needed, judge, run, situate
from midwife.types import Budget

source = Path("examples/upgrade.json").read_text()
frame = situate(json.loads(source))

kept_run = load_records("examples/runs/upgrade/1.jsonl")
[finding] = judge(frame, kept_run)
print(finding.category, finding.evidence)
print(finding.obligations)

kept = []
budget = Budget(calls=calls_needed(frame))
run(frame, EGemma(), budget, on_record=kept.append)
[finding] = judge(frame, kept)
```
<!-- end:use -->

---

### Learn more

The documentation site is built from `docs/`, and every page reads on GitHub
too.

- **[The examples](https://mirzahusadzic.github.io/gadfly/examples/):** experiments that climb one
  capability a step, each with its predictions and kept runs.
- **[Write a frame](https://mirzahusadzic.github.io/gadfly/write-a-frame):** every key, and what the parser
  refuses.
- **[Reading a verdict](https://mirzahusadzic.github.io/gadfly/reading-a-verdict):** the rules in order,
  evidence apart from obligations, several inputs, and stopped runs.
- **[Statistics](https://mirzahusadzic.github.io/gadfly/statistics):** how firm a verdict is over its kept
  runs, beside it and never changing it.
- **[Crossings](https://mirzahusadzic.github.io/gadfly/crossings):** a decision made from something
  written from the evidence, with the maker inside the reading.
- **[Recoil](https://mirzahusadzic.github.io/gadfly/recoil):** a piece found deep in a chain of
  frames, carried back across its crossings to the hole it fits, asked until firm.
- **[Batteries](https://mirzahusadzic.github.io/gadfly/batteries):** the shipped scorers, their privacy
  guarantees, and writing your own.
- **[Architecture and limits](https://mirzahusadzic.github.io/gadfly/architecture):** what Gadfly keeps, and
  what a verdict does not claim.
- **[Python API](https://mirzahusadzic.github.io/gadfly/reference):** every public function and class.

---

### Cite

The working paper, on Zenodo under CC BY 4.0, describes the method, this
library and its examples' evidence; its DOI always resolves to the latest
version:

```bibtex
@misc{husadzic2026loadbearing,
  author    = {Husadzic, Mirza},
  title     = {When Meaning Is Load-Bearing: Testing Whether
               a Decision Rests on Its Declared Evidence},
  year      = {2026},
  publisher = {Zenodo},
  note      = {Working paper},
  doi       = {10.5281/zenodo.23962158},
  url       = {https://doi.org/10.5281/zenodo.23962158}
}
```

---

### Develop

The suite needs no model and no network. These commands run it, lint, bring
the docs' transcripts, copies and reference back in line with the code, and
build the docs site with VitePress, on Node 24 or later:

```bash
uv sync
uv run pytest
uv run ruff check midwife examples tests tools
uv run ruff format --check midwife examples tests tools
uv run python tools/doc_outputs.py --write
npm ci
npm run docs:build
```

`docs:build` writes the site to `docs/.vitepress/dist` and fails on a dead
link, and `npm run docs:dev` serves one that follows your edits. The After the
Poem replay runs when `GADFLY_ATP_PLANS` names its plans.

---

[Upgrading](https://mirzahusadzic.github.io/gadfly/upgrading) · [Troubleshooting](https://mirzahusadzic.github.io/gadfly/troubleshooting) · [Fonts and libraries](https://mirzahusadzic.github.io/gadfly/notices) · [Apache-2.0](https://github.com/mirzahusadzic/gadfly/blob/main/LICENSE) · [The essay under CC BY 4.0](https://github.com/mirzahusadzic/gadfly/blob/main/LICENSES/CC-BY-4.0.txt)
