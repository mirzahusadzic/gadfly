# Repository guide

Gadfly tests whether a decision rests on the evidence it is said to rest on: a frame declares the relation, fixed interventions cut or change it, a battery reads each trial, and fixed rules read the verdict. Python 3.13 or later, no runtime dependencies; the package is `midwife`, the command `gadfly`. Prefer focused fixes over new trials, rules, commands or dependencies.

---

### Map

- Docs: `README.md` (the quick path), `docs/` (the site, by reader), `docs/load-bearing.md` (the author's CC BY 4.0 essay), `docs/reference.md` (from the docstrings).
- Dev: `uv sync`; `uv run pytest` runs offline against fakes. The site: Node.js 24, `npm ci`, `npm run docs:dev` or `docs:build`.

| Task | Source |
| --- | --- |
| Frames: parsing, canonical JSON, hash | `midwife/frame.py`, `midwife/frame.schema.json` |
| Refusals and warnings, each a class with its exit status | `midwife/errors.py`, held by `tests/test_errors.py` |
| Trials, prompts, renaming, placement | `midwife/interventions.py` |
| The run loop, budget, cancellation, records | `midwife/pipeline.py`, `midwife/types.py` |
| Verdict rules, levels, evidence, obligations | `midwife/verdict.py` |
| Several frames counted, never combined | `midwife/portfolio.py` |
| Statistics beside a verdict: intervals, tests, power, stability, pooling | `midwife/stats.py`, `gadfly stats` |
| Command line | `midwife/cli.py` |
| Batteries: the shared loopback call and label pointer, then the shipped ones | `midwife/batteries/critic.py`; `unified.py`, `egemma.py`, `local_json.py`, `tendora.py` (its live test runs only with `TENDORA_PACKAGE`), `crossing.py` (a maker then a reader, across a boundary) |
| Example frames, their kept runs, predictions, results and findings | `examples/*.json`, `examples/runs/<frame>/`, `examples/*.md`; read back with `examples/read.py`, run with `examples/climb.py` |
| The payments demo's kept runs (Tendora's engine and Gemma), played by the watch view | `examples/payments-demo/`, `docs/examples/watch.md` |
| Generated docs: transcripts, copies, the API page, frames in words, `frames.json` | `tools/doc_outputs.py` |
| The watch view's data | `tools/watch_data.py`, written to `docs/public/assets/watch/` |
| The site: sidebar, Markdown rules, theme, the troubleshooting JSON view | `docs/.vitepress/` (`config.mjs`, `markdown.mjs`, `theme/`, `theme/errors.js`) |

---

### Preserve these behaviors

- **Fixed rules.** A verdict follows from the records by `midwife/verdict.py`'s rules, in their order; no model judges. A rule change is a method change: say so in the docs and test every category it touches.
- **Frames and records.** A frame is hashed whole, as canonical JSON, and never defaulted, rewritten or repaired. Every record names its frame's hash, and `check_records` refuses records another plan, frame or battery made.
- **Findings.** Unresolved names the open check; evidence and obligations stay apart, and an obligation is not a passed check.
- **Trial blindness.** A battery gets the frame and the prompt, never the trial's id.
- **Runs.** `run` never starts a call the budget cannot cover and hands each record on as it exists. The command line never writes over a records file, and a refusal spends nothing and makes no file.
- **Batteries.** Loopback only: no proxy, no redirects, no tools. Credentials never reach a request body, a record or a log. The unified battery sends each call under the router's deny data policy, and refuses a router that does not list it, unless the frame names the exact slug under `trainsOnInputs`, and refuses OpenAI slugs. A failed or timed-out call is an opening, never a label and never dropped.
- **Kept runs.** `examples/*.json`, `examples/runs/` and the predictions never change after their runs: a new idea is a new frame with fresh runs.

#### Command line, errors and warnings

The command line follows [clig.dev](https://clig.dev/), and its errors are Python's (PEP 8, 20, 230, 352, 3151 and 678), so a person, a script and another model read them alike. `docs/troubleshooting.md` tables every exit status and message, and its tests hold it to the code.

- Results go to standard output or the file named, messages to standard error. Any file may be `-`, read once and refused at a terminal; every command takes `--json`; flags are matched in full only.
- A refusal is a class for what to fix, its exit status an attribute: `UsageError` 2, `FrameError` 4, `RecordsError` 5, `BatteryError` 6, Python's own file errors 7, `KeyboardInterrupt` 130. It prints as a traceback's last line, `Type: message`, then each note; with `--json`, `{"error": {"type", "exit", "message", "notes", "help"}}` on standard error. Anything else raised, a battery's `SystemExit` too, is a bug: its traceback, and 70. A second Ctrl-C with calls still out exits at once; a closed reader ends `gadfly` quietly (SIGPIPE, 141).
- What a run did not do as asked, though it went on, is a warning raised with `warnings.warn`, printed the same way, or with `--json` listed under `warnings` in `run`'s one result: `OpeningWarning` 1 (only when every call opened), `StoppedWarning` 3. Nothing passes in silence, and an empty result means only "none".
- A message names the kind of thing and quotes its value, as Python's own do, then says what went wrong and where (`file 'kept.jsonl' holds a lone surrogate at line 3`); a note says why and what to do, and someone else's words go in a note, quoted ("it said '...'"). Outside a quoted value, no line Gadfly prints holds a second colon: a frame's name, span ids, input ids and labels must be one plain name (`midwife.errors.is_plain`), and other free text prints quoted when it would break a line (`plain`). `tests/test_errors.py` reads the source to hold all of this.

---

### Docs

Every page reads the same on GitHub as on the site. The site may add a second view built from the page, as the troubleshooting tables' JSON view does; nothing of it is written in the Markdown.

- GitHub syntax only: GitHub alerts, never `!!!`, `--8<--`, attribute lists, Markdown divs or `:::` lines (`tests/test_docs.py` refuses them).
- Readers first: never a JSON or JSONL dump in front of a reader. A frame is shown in words between `<!-- frame PATH -->` and `<!-- end frame -->`, a table for each part in the order a run uses it, ending with "The frame as written ↗", a relative link to its `.json`; on the site that opens `/frames/<stem>`, the file with numbered `#L` lines and the hash its records name. A short fragment of what to type, and a battery's wire format, stay code; kept runs are read through `examples/read.py` transcripts and the watch view.
- Generated text is never edited by hand: transcripts (a ```` ```text ```` block whose `$` lines run from the root), copies (`<!-- copy SRC -->`), the API page (`<!-- api MODULE -->`), frames in words and `docs/.vitepress/frames.json` come from `uv run python tools/doc_outputs.py --write`, the watch data from `uv run python -m tools.watch_data --write`. Tests fail on drift.
- Shape: `#` for the title only; `###` sections under a `---` rule, parts `####`; a lead or paragraph of three sentences at most; tables only for tabular data (question-to-answer and troubleshooting tables too), every cell filled, bold run-in lists otherwise; a sentence before each code block, no comments inside, lines of about 60 characters wrapped with `\`; one alert a section at most, never two in a row; each link once a page; troubleshooting last.
- Move text, don't drop it. `test_every_link_lands` checks every relative link and anchor; every page is in the sidebar or `srcExclude`, a route's template aside.
- Site text: sentence case and plain words, no "·" separators, no colons as label separators (the README may end in a row of links split by "·"). Colours are tokens in `theme/custom.css`; no text under 15px but code (14px); weights 400 and 600; motion only where it carries something; a state shown by more than colour.
- Docs stay generic: Gadfly's own contract, not any caller's use.

---

### Validate and commit

- Checks: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` (85% coverage; `GADFLY_ATP_PLANS` adds the After the Poem replay) and `npm run docs:build`, which fails on a dead link. CI runs them on Python 3.13 to 3.15, every action pinned to its release's commit.
- A behavior change or a fix comes with a test that fails on the old code and passes after.
- A live run spends a provider's calls: count them first (`gadfly plan`, `calls_needed`), and run only when the task includes it.
- Release, in two pushes: first the commit that bumps `pyproject.toml`, `midwife/__init__.py` and `uv.lock` to the new version; then, only once CI on that commit has passed on every Python, its tag `vX.Y.Z`. The tag runs `.github/workflows/publish.yml`, which tests on one Python, builds and publishes `midwife` to PyPI by trusted publishing, and PyPI never takes a version twice. The site publishes from `main` once CI has passed.
- Commits only when asked; never push. Subject `area: what changed` in at most 72 characters, a blank line, then a body hard-wrapped at 72 (`git log --format=%B origin/main..main | awk 'length > 72'`).
