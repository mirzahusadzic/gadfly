# Repository guide

Gadfly tests whether a decision rests on the evidence it is said to rest on: a frame declares the relation, fixed interventions cut or change it, a battery reads each trial, and fixed rules read the verdict. A Python 3.13 library with no runtime dependencies. Prefer focused fixes over new trials, verdict rules, commands or dependencies.

---

### Map

- Docs: `README.md` (the quick path), `docs/` (the site's pages, sorted by reader), `docs/load-bearing.md` (the essay, CC BY 4.0), `docs/reference.md` (written from the docstrings).
- Dev: `uv sync`; `uv run pytest` runs offline against fakes, without a model or credentials. The site: Node.js 24, `npm ci`, `npm run docs:dev` or `docs:build`.

| Task | Source |
| --- | --- |
| Frame parsing, canonical JSON, hash, refusals | `midwife/frame.py`, `midwife/frame.schema.json` |
| Trial planning, prompts, renaming, placement | `midwife/interventions.py` |
| Run, budget, cancellation, records | `midwife/pipeline.py`, `midwife/types.py` |
| Verdict rules, levels, evidence, obligations | `midwife/verdict.py` |
| Several frames counted, never combined | `midwife/portfolio.py` |
| Command line | `midwife/cli.py` |
| What every critic shares: the loopback call, the label pointer | `midwife/batteries/critic.py` |
| The shipped batteries | `midwife/batteries/unified.py` (the model router), `egemma.py`, `local_json.py`, `tendora.py` (Tendora's engine; its live test runs only with `TENDORA_PACKAGE`) |
| Example frames and their kept runs | `examples/*.json`, `examples/runs/<frame>/` |
| The payments demo's kept runs (Tendora's engine and Gemma, copied from the tendora repository) | `examples/payments-demo/`, played by `docs/demo.md` |
| Predictions, results, findings | `examples/PREDICTIONS.md`, `examples/RESULTS.md`, `examples/FINDINGS.md` |
| Reading kept runs back; running a frame against eGemma | `examples/read.py`; `examples/climb.py` |
| Quoted outputs, copies, the API page, frames shown in words | `tools/doc_outputs.py` |
| A frame's source page on the site, and the frames it publishes | `docs/frames/`, `docs/.vitepress/frames.json` (written by `tools/doc_outputs.py`) |
| The watch view's data | `tools/watch_data.py`, written to `docs/public/assets/watch/` |
| The site: sidebar, Markdown rules, theme, footer | `docs/.vitepress/config.mjs`, `docs/.vitepress/markdown.mjs`, `docs/.vitepress/theme/` |

---

### Preserve these behaviors

- Fixed rules: a verdict follows from the records by the rules in `midwife/verdict.py`, in their order; no model judges. A rule change is a method change: say so in the docs and test every category it touches.
- A frame is hashed whole, as canonical JSON. Every record names its frame's hash, and `check_records` refuses records another plan, frame or battery made. Never default, rewrite or repair a frame.
- Unresolved names the open check; evidence and obligations stay apart, and an obligation is not a passed check.
- Trial blindness: a battery gets the frame and the prompt, never the trial's id.
- `run` never starts a call the budget cannot cover and hands each record on as it exists; the command line never writes over a records file.
- Shipped batteries: loopback only, no proxy, no redirects, no tools. Credentials never reach a request body, a record or a log. The unified battery sends `data_collection: deny` unless the frame names the exact slug under `trainsOnInputs`, and refuses OpenAI slugs. A failed or timed-out call is an opening, never a label and never dropped.
- `examples/*.json` and `examples/runs/` never change after their runs: a new idea is a new frame with fresh runs, and predictions are written before the first call.

---

### Docs

Every page reads the same on GitHub as on the site.

- GitHub syntax only: GitHub alerts, never `!!!`, `--8<--`, attribute lists, Markdown divs or `:::` lines; `tests/test_docs.py` refuses them.
- Readers first, machine data second. Never put a JSON or JSONL dump in front of a reader; `test_no_page_shows_a_whole_frame_as_json` refuses a whole frame as code.
- A frame is shown in words: `<!-- frame PATH -->` and `<!-- end frame -->` hold its readable view, a table for each part in the order a run uses it (the claim, the evidence with the anchors marked `*` and each span linked to its `#L` line in the file, the question, the trials as `plan` gives them with what each tests, how the answers are read, and the setting), which `uv run python tools/doc_outputs.py --write` writes; `test_every_frame_shown_in_words_is_its_frame` keeps it current.
- The source is one link away: the view ends with "The frame as written ↗", a relative link to the `.json`. GitHub opens its own numbered file view; on the site a Markdown rule sends any link to a published frame's file to its source page, `/frames/<stem>`, which shows the file with numbered `#L` lines, the hash its records name (from `digest`), a way back to the words, and the file to download. `docs/.vitepress/frames.json` lists the published frames, every example and every frame a page shows; `tools/doc_outputs.py` writes it and `test_the_site_publishes_each_frame_with_the_hash_its_records_name` holds it.
- A short fragment that shows what to type for one key stays as code, and so does a battery's wire format. Kept runs are read through `examples/read.py` transcripts and the watch view, never as JSONL.
- Generated text is never edited by hand: transcripts (a ```` ```text ```` block whose `$` lines run from the root), copies (`<!-- copy SRC -->`), the API page (`<!-- api MODULE -->`), frames shown in words (`<!-- frame PATH -->`) and `docs/.vitepress/frames.json` come from `uv run python tools/doc_outputs.py --write`; the watch data from `uv run python -m tools.watch_data --write`. Tests fail when either drifts.
- Shape: `#` for the title only; top-level sections are `###` headings under a `---` rule, parts `####`; section leads of two or three sentences at most, and no paragraph over three; tables only for tabular data, bold run-in lists otherwise (question-to-answer and troubleshooting tables are fine), every cell filled; a sentence before each code block, no comments inside, lines of about 60 characters, wrapped with `\`; at most one alert per section, never two in a row; each link once per page; troubleshooting last.
- Move text, don't drop it. `test_every_link_lands` checks every relative link and anchor (GitHub's slugs, and `#L` lines in a file); every page is in the sidebar or in `srcExclude`, except a route's template such as `docs/frames/[frame].md`.
- Site text (the pages under `docs/` and the theme): sentence case and plain words; no "·" separators and no colons as label separators. The README, read on GitHub and PyPI rather than the site, may end in a row of links split by "·", as the router's does. Motion only where it carries something.
- Theme: each study's colours are tokens in `docs/.vitepress/theme/custom.css`; no text under 15px except code (14px); weights 400 and 600 only.
- Docs stay generic: they describe Gadfly's own contract, not any caller's use.

---

### Validate and commit

- Checks: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` (85% coverage; `GADFLY_ATP_PLANS` adds the After the Poem replay) and `npm run docs:build`, which fails on a dead link. CI runs them on Python 3.13 to 3.15.
- A behavior change or a fix comes with a test that fails on the old code and passes after.
- A live run spends a provider's calls: count them first with `gadfly plan` or `calls_needed`, and run only when the task includes it.
- Release: a tag `vX.Y.Z` that names `pyproject.toml`'s version runs `.github/workflows/publish.yml`, which tests, builds, checks and publishes the `midwife` package to PyPI by trusted publishing; the site publishes from `main` once CI has passed. CI pins every action to its release's commit.
- Commits only when asked; never push. Subject `area: what changed` in at most 72 characters, a blank line, then a body hard-wrapped at 72; check with `git log --format=%B origin/main..main | awk 'length > 72'`.
