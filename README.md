# Gadfly

[![CI](https://github.com/mirzahusadzic/gadfly/actions/workflows/ci.yml/badge.svg)](https://github.com/mirzahusadzic/gadfly/actions/workflows/ci.yml)
[![midwife on PyPI](https://img.shields.io/github/v/tag/mirzahusadzic/gadfly?sort=semver&label=midwife&logo=pypi&logoColor=white)](https://pypi.org/project/midwife/)

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
passed check. Under the default `carriage: all-checks`, a category waits
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

Each shipped battery calls a service on loopback. Start the service and give
Gadfly its key; the address has a default.

- **eGemma, for Gemma 4 on this machine:** install and start
  [eGemma](https://github.com/mirzahusadzic/egemma) as its README says. Gadfly calls it at
  `EGEMMA_URL`, by default `http://127.0.0.1:8000`, with the key from the
  file named by `EGEMMA_API_KEY_FILE`, else `EGEMMA_API_KEY`. A frame names it
  as `"battery": {"kind": "egemma"}`, as every example does.
- **The unified model router, for Claude, DeepSeek and OpenRouter's
  models:** install and start the [router](https://github.com/mirzahusadzic/codex-unified-model-router) as its README says.
  Gadfly calls it at `http://127.0.0.1:18766`, with its token from
  `CODEX_ROUTER_TOKEN`, else the router's settings file,
  `~/.codex/unified-router/openrouter.env`. A frame names its model, as
  `"battery": {"kind": "unified", "model": "anthropic/claude-sonnet-5-5"}`,
  and the router's `GET /v1/models` lists the ones it serves.
- **`local-json`, for an evaluator of your own:** a service on this machine at
  the frame's `battery.url` that answers JSON, with no key.
- **Tendora's engine, for a Tendora project's own answers:** start the
  engine server from Tendora's demo package on a project, as the package's
  README says. A frame names it as `"battery": {"kind": "tendora", "url":
  ...}`, with no key, and each input is a saved check's own case and
  question.
- **Your own class:** any class whose `name` is the frame's `battery.kind`,
  passed to `run` as `--battery module:Class`.

These two commands make ten calls to eGemma and read the verdict, a quick
check that the battery answers:

```bash
uv run gadfly run examples/rung1.json \
  --battery midwife.batteries.egemma:EGemma \
  --calls 10 --out check.jsonl
uv run gadfly report examples/rung1.json check.jsonl
```

---

### Use

Every example is a real experiment: a frame, the predictions written before
its first call, and the records of each run, read by Gemma 4 26B through
eGemma. Reading one back calls no model:

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
command and flag.

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

- **The battery is part of the frame:** `battery.kind` must equal the
  battery's `name`, and another battery is another frame, so call `situate()`
  again when you swap it.
- **Several inputs:** `overall(judge(frame, kept))` returns one category over
  all of them.
- **A stopped run:** `run(..., kept=kept)` continues it, and records already
  in `kept` are not made again.

---

### Learn more

The documentation site is built from `docs/`, and every page reads on GitHub
too.

- **[The examples](https://mirzahusadzic.github.io/gadfly/examples/):** experiments that climb one
  capability a step, each with its predictions and kept runs.
- **[Write a frame](https://mirzahusadzic.github.io/gadfly/write-a-frame):** every key, and what the parser
  refuses.
- **[Reading a verdict](https://mirzahusadzic.github.io/gadfly/reading-a-verdict):** the rules in order, and
  evidence apart from obligations.
- **[Batteries](https://mirzahusadzic.github.io/gadfly/batteries):** the shipped scorers, their privacy
  guarantees, and writing your own.
- **[Architecture and limits](https://mirzahusadzic.github.io/gadfly/architecture):** what Gadfly keeps, and
  what a verdict does not claim.
- **[Python API](https://mirzahusadzic.github.io/gadfly/reference):** every public function and class.

---

### Develop

The suite needs no model and no network. These commands run it, lint, and
bring the docs' transcripts, copies and reference back in line with the code:

```bash
uv sync
uv run pytest
uv run ruff check midwife examples tests tools
uv run ruff format --check midwife examples tests tools
uv run python tools/doc_outputs.py --write
```

The After the Poem replay runs when `GADFLY_ATP_PLANS` names its plans.

#### The docs site

The site is built with VitePress from `docs/`, on Node 24 or later:

```bash
npm ci
npm run docs:dev
npm run docs:build
```

`docs:dev` serves a site that follows your edits, and `docs:build` writes it
to `docs/.vitepress/dist`, failing on a dead link.

---

[Troubleshooting](https://mirzahusadzic.github.io/gadfly/troubleshooting) · [Fonts and libraries](https://mirzahusadzic.github.io/gadfly/notices) · [Apache-2.0](https://github.com/mirzahusadzic/gadfly/blob/main/LICENSE) · [The essay under CC BY 4.0](https://github.com/mirzahusadzic/gadfly/blob/main/LICENSES/CC-BY-4.0.txt)
