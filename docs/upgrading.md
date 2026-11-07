# Upgrading

Each release that changes what a caller meets has a section here, the newest
first. In none of them does a verdict change: every kept run reads to the same
category. The site follows `main`, so a release not yet out says so.

Just after a release, PyPI can take a few minutes to list the new version,
and until then uv answers that it does not exist. Wait a few minutes, then
`--refresh-package midwife` makes uv look again, past its own cache.

---

### To 0.13.1, not yet released

No verdict, record or frame changes. On Windows, these things a caller of 0.13.0 meets do change:

| In 0.13.0 | In 0.13.1 | What to do |
| --- | --- | --- |
| Piped, standard output took Windows's code page under Python 3.13 and 3.14, so a character outside it, such as ✓ in a frame, ended the command as a bug (70), and standard error printed it as an escape | Both carry UTF-8 on every platform, as Gadfly's files do | A script that decoded Gadfly's output in the code page decodes UTF-8 |
| Nothing ended the command quietly when its reader stopped reading, since Windows has no SIGPIPE | It ends quietly with 141, the status SIGPIPE gives on Linux and macOS | Nothing |

New:

- **Linux, macOS and Windows:** CI runs the tests on each, for Python 3.13, 3.14 and 3.15, and the package says so in its classifiers.

---

### To 0.13.0

No verdict or record-format changes, and a frame without the new keys keeps its hash and reading. These things a caller of 0.12.0 meets do change:

| In 0.12.0 | In 0.13.0 | What to do |
| --- | --- | --- |
| `gadfly firm`'s last line ended with the calls made now | It goes on with the tokens those calls reported and how many reported no reasoning | A script that reads that line reads `firm --json` instead, whose `usage` and `unthought` hold the same counts |
| `--most` on `firm`, `gate` and `plan`, and `most` in `until_firm` and `calls_until_firm`, defaulted to 5 | They default to the frame's `standing.most`, else 5, and refuse a different value for a frame that declares one | Nothing, for a frame that declares none |
| The `--json` of `run`, `firm` and `report` held what 0.12.0 printed | Each holds new fields, `usage` and `unthought`, and `report`'s `records` too | Nothing; no field was removed or renamed |

New:

- **Calls at once while asking until firm:** `until_firm(..., parallel=N)` and `gadfly firm --parallel N` make up to N calls at once within each run, for a battery that takes them, as `run`'s `parallel` does. The runs stay one after another, and a battery that takes one call at a time is refused before any call, in `run`'s words.
- **The readers' tokens beside firmness:** `gadfly firm` ends its last line with the tokens the calls made now reported, in and out and how many of those out were reasoning, and `--json` and `until_firm`'s result give them as `usage`, each count by name. `run --json` gives the same `usage` beside `made`, and `report --json` gives it beside `records`, the records it read. Nothing is estimated: a count no call reported is absent.
- **Calls that reported no reasoning:** `run --json`, `firm --json` and `report --json` give `unthought`, of the calls that reported reasoning tokens how many reported 0, by trial too, and `firm` ends its last line with the count; in Python, `midwife.pipeline.unthought(records)` and `Firm.unthought`, beside `summed_usage(records)`. It is reported only: nothing is resent and no answer is set aside.
- **The most runs a frame is read in, declared:** a frame may give `standing.most`, the most runs asking it until firm reads, so its hash names it. `firm`, `gate`, `plan` and `until_firm` read it, and refuse a different `--most` or `most`; a walk counts a fit by its own. A frame without it keeps its hash and the default, 5.
- **`--calls auto`:** on `run`, a whole run's calls (`calls_needed`); on `firm`, the most `--most` runs can take beyond the kept ones (`calls_until_firm`). A number works as before.
- **Text withheld before any call:** `--withhold FILE` on `run`, `firm` and `check-frame`, and `withhold=` on `run` and `until_firm`, refuse a frame whose prompts hold text a withhold set names (`midwife.withhold`). Its `always` part binds every call, and its `training` part binds a battery whose calls may train, which a battery says with an optional `trains(frame)`; the unified battery says yes only when the frame names its model under `trainsOnInputs`, and the local batteries say no.

---

### To 0.12.0

No verdict changes, and these things a caller of 0.11.0 meets do:

| In 0.11.0 | In 0.12.0 | What to do |
| --- | --- | --- |
| The `unified` battery refused, before any call, a model whose slug began `ultra-spark/` or `openrouter/meta/` unless the frame named that exact slug under `trainsOnInputs`, so the non-training Muse Spark 1.3 ran only with consent to training it does not do | Which models train is the router's to say: without `trainsOnInputs`, each call goes under the deny data policy, and the router refuses a model it declares training-tier, as an opening that names it | Name a training model under `trainsOnInputs` as before; a non-training one, such as `openrouter/meta/muse-spark-1.3`, now runs without it, under the deny policy |
| `midwife.batteries.unified.TRAINS_ON_INPUTS` held the battery's prefixes of training models | The name is gone, and importing it raises `ImportError` | Keep your own list of the exact slugs you consent to, and name each under `trainsOnInputs` |

New:

- **`StopRun`:** a battery or a maker raises `midwife.errors.StopRun(reason)` when its harness fails. The run ends as a spent budget ends it, a `StoppedWarning` with exit 3 that quotes the reason, and `--kept` finishes it once the harness is fixed.
- **Private Ultra Spark:** `ultra-spark-private/` slugs go to the router, which the `unified` battery refused before as an OpenAI slug.

---

### To 0.11.0

No verdict changes, and these things a caller of 0.10.0 meets do:

| In 0.10.0 | In 0.11.0 | What to do |
| --- | --- | --- |
| A frame with two holes the piece fits was one line of `Walk.lines()` and of `gadfly walk`, naming both | It is one line for each hole, in the order the walk would ask it; `fits` in a line names its one hole | Read a hole a line; a frame with one such hole reads as before |
| A `unified` record's `served` ended with the provider or the pinned endpoint | It ends with the route the router names, as `(route anthropic)` | A reader of `served` stops at ` (route ` for the model and provider |

New, and opt-in:

- **Salience:** a hole may say what it is read for, under `about`, and its
  `salience`, `consider` or `defer`. A walk lists a deferred fit under
  `deferred`, kept and not asked.
- **A budget:** every considered fit is a `Fit` in `order`.
  `walk(..., calls=N, most=M)` and `gadfly walk --calls N --most M` count
  each fit's calls until firm before the first, and list those the calls
  cannot cover as not asked.
- **Vectors:** `walk(..., vectors=read_vectors(data))` and `--vectors FILE`
  order the fits by cosine, from whole-text vectors a caller acquired, and
  only order them.
- **Artefacts:** `walk(..., made=[run])` and `--made FILE` take a crossing's
  records, so a frame quoting an artefact its maker made climbs to the
  crossing.
- **Sideways:** `walk(..., sideways=True)` and `--sideways` offer the piece
  one step aside too, to each frame quoting a text the start frame quotes.
- **Reasoning tokens:** the `unified` battery keeps each count of a
  provider's usage breakdown in the record, such as `reasoning_tokens`, so a
  record says whether a call thought.
- **Claude on Anthropic's API:** `"fallback": "none"` in a `unified` battery
  line, or a crossing's maker line, keeps an `anthropic/` model's calls on
  Anthropic's API, and a refusal there is an opening.
- **A thinking budget:** `"thinkingBudget": N` gives a Claude model that
  still takes a budget a fixed one on every call, in place of `reasoning`;
  `run` refuses a cap on each answer that is not above it. Both need a router
  that lists them at `GET /health`.
- **`check_cap`:** a battery may refuse, before any call, a cap on each
  answer it cannot answer within.
- **What a walk returns:** `Walk` adds `order`, `deferred`, `unasked`,
  `budget`, `most`, `space`, `vectors`, `made` and `siblings`, and each
  `Fit` holds `frame`, `hole`, `cosine`, `unordered`, `calls`, `asked`,
  `made` and `sideways`. `gadfly walk --json` adds `order`, `deferred`,
  `budget`, `most`, `space` and `vectors`, and `sideways` and `made` on
  each frame; its text adds the `deferred:`, `ordered:` and `budget:` lines.

---

### To 0.10.0

No verdict changes, and this thing a caller of 0.9.1 meets does:

| In 0.9.1 | In 0.10.0 | What to do |
| --- | --- | --- |
| A successor that added, changed or dropped a hole besides the one it filled, or closed it with a span of another kind, asked the same question | `reframes` lists `holes`, and `gate` reads the successor as a reframing | Close only the hole the piece fills, with a span of its kind; the other holes may stay in any order. A frame that takes in more is a new frame |

New: `successor(..., after=SPAN)` and `gadfly successor --after SPAN` place
the piece right after the line it amends, for a reader that reads each span
as a line; its ablation is still the frame's body byte for byte.
`gadfly successor --text TEXT --kind KIND` takes a piece found in no frame,
as `Piece(text, kind)` does in Python. `recoil.calls_until_firm` and
`gadfly plan --most N --runs FOLDER` count the most calls asking until firm
can make, before the first.

---

### To 0.9.1

No verdict changes, and nothing a caller of 0.9.0 meets changes. New, and
opt-in: the `tendora` battery's `readings` flag sends a reading beside each
statement, for an engine that takes them, and holds the reply to naming each
one it was sent.

---

### To 0.9.0

No verdict changes, and these five things a caller of 0.8.0 meets do:

| In 0.8.0 | In 0.9.0 | What to do |
| --- | --- | --- |
| An endpoint tag with a space or a control character inside it went to the router | It is refused before any call, a `BatteryError` (6), for a reader's line and a crossing maker's alike | Name each tag as the router lists it |
| A router trickling its `GET /health` answer could hold the check past the battery's timeout | The answer is read whole within the timeout, or the run is refused as before, when the router cannot be asked | Nothing, with a router that answers in time |
| A call pinned to one endpoint, whose answer named no provider, recorded the model alone in `served` | It records that endpoint's tag too, as 0.8.0 said | Nothing |
| `report`, `plan` and `check-frame` printed a frame name ending in a colon bare | They print it quoted, as `stats` does | Nothing; the frame's hash is unchanged |
| A mistyped required flag, such as `run --battry`, was refused as the flag missing | It is named, `unrecognized arguments --battry`, before any flag that is missing; the status is 2 as before | Nothing, unless a script read the old words |

New, and opt-in: `gadfly stats` and `midwife.stats`, which say beside each
verdict how firm it is over the kept runs; `gadfly plan --agreement`,
which says before a run how often its quorum can reach a level; and a span's
`source`, the SHA-256 of the text it crossed with, which the parser holds it
to. The `crossing` battery has a maker write an artefact from each trial's
body and a reader decide from it, so a frame tests a decision made on the
far side of a boundary; `midwife.batteries.unified.request_body` builds the
router request both sides send.

A frame may also declare `holes`, what its body is missing, and `offers`, the
kind its decision climbs as; a frame without them keeps its hash. A frame
whose anchors are all holes is walked, never planned: `plan` and
`calls_needed` refuse it with a `FrameError` until a hole is filled.
`midwife.recoil` carries a piece found further down a chain of frames up to
the holes it fills, and asks each fit again until its verdict is firm, as
[Recoil](recoil.md) shows.

Each recoil step is also a command, `gadfly walk`, `successor`, `firm` and
`gate`, whose `--json` prints what its function returns. `until_firm` says a
stop for its budget as a `StoppedWarning`, as `run` does, and given no
battery it reads the kept runs alone.

---

### To 0.8.0

0.8.0's `unified` battery speaks to the router only through the router's own
headers, its data policy, its endpoint pins and its report of what served a
call, and needs a router that takes them.

| In 0.7 | In 0.8.0 | What to do |
| --- | --- | --- |
| The `unified` battery asked for endpoints that keep no data with a field in each request's body | Each call goes under the router's `X-Codex-Router-Data-Policy: deny`, unless the frame names its model under `trainsOnInputs` | Nothing, with a router that takes it |
| A call went to the router unasked | Before the first call, the battery reads the router's `GET /health`, and refuses to run, a `BatteryError` (6), when the router does not list the policy or cannot be asked | Update the router, or start it |
| A model whose provider trains, by the router's list but not Gadfly's, went out with that field | The router refuses it, and the call comes back as an opening that names the model | Choose another model, or name it under `trainsOnInputs` |
| `battery.endpoints` went out as a field in each request's body | It goes as the router's `X-Codex-Router-Endpoints`, up to 16 tags with no comma or space, and a router whose `GET /health` does not list endpoint pins is refused before any call | Update the router; keep a pin to 16 tags |
| `served` named the model, and an endpoint only when a header the router never sent was there | It names the model, then the provider the router reports, or the tag of a single pinned endpoint; a provider the router does not yet know is left out | Nothing; read the provider from `served` when it is there |

---

### To 0.7.0

0.7.0 changes what the command line prints and how it ends, and how Gadfly
raises what it refuses; this lists what a caller of 0.6.0 meets, and what to
do. 0.7.1 changes nothing a caller meets: one test that read a refusal's
message now passes on Python 3.14 and later, as on 3.13.

#### The command line

| In 0.6.0 | In 0.7.0 | What to do |
| --- | --- | --- |
| A refusal printed `gadfly: <reason>` and exited with 2 | It prints `Type: message`, then each note on a line of its own, and exits with its class's status: `UsageError` 2, `FrameError` 4, `RecordsError` 5, `BatteryError` 6, a file error 7 | Read the status or the class; [Troubleshooting](troubleshooting.md) tables each message |
| Any other exception was Python's traceback, exiting with 1 | It is a bug: its traceback, and 70 | Report it |
| `check-frame` exited with 1 on a problem | It prints each problem as a `FrameError` and exits with 4 | Read 4 as refused |
| A run its budget cut short exited with 0, after a `stopped:` line | It exits with 3, after a `StoppedWarning` | Read 3 as a partial run, or raise the budget |
| Openings were an `openings:` line in `run`'s summary | They are an `OpeningWarning`; `run` exits with 1 only when every call opened, as before | Read the warning instead of the line |
| A shortened flag, such as `--stop`, was taken | Flags are named in full; `-o` and `--output` name `--out` | Write each flag in full |
| A closed reader, as with `\| head`, ended `gadfly` with a traceback | It ends quietly, with 141 | Nothing |

Any file Gadfly reads may now be `-`, standard input, which is refused at a
terminal. `run --out -` streams the records to standard output and its summary
to standard error, and a run with nothing left to ask makes its file, empty.

#### JSON output

| Command | In 0.6.0 | In 0.7.0 |
| --- | --- | --- |
| any refusal with `--json` | `gadfly: <reason>` on standard error, as text | One object on standard error, `{"error": {"type", "exit", "message", "notes", "help"}}` |
| `run --json` | `stopped` and `openings` in its result | Its result also holds `exit`, and `warnings`, each with the status it gives |
| `check-frame --json` | `{"ok": false, ...}` on standard output for a refused frame | One `FrameError` object on standard error that lists `problems`, each with its notes; `{"ok": true, ...}` on standard output for an accepted one |

#### Frames and Python callers

| In 0.6.0 | In 0.7.0 | What to do |
| --- | --- | --- |
| A frame's name, span ids, input ids and labels could hold `": "` or a line break | Each must be one plain name, or the frame is refused | Rename it; a new name is a new frame, with a new hash |
| A refusal was a `ValueError`, and a missing eGemma key or router token a `RuntimeError` | Each refusal is a class in `midwife.errors`, still a `ValueError`; the missing key or token is a `BatteryError` | Catch `midwife.errors.GadflyError`, or the class you mean |
| `run()` reported openings and a stop only in its result | It also raises `OpeningWarning` and `StoppedWarning` with `warnings.warn` | Filter them, or make them errors, as with `-W error::midwife.errors.OpeningWarning` |
| A Ctrl-C in `run()` raised a plain `KeyboardInterrupt` | Its `running` says how many calls are still out | Read it before you exit |

New, and opt-in: `run(stop_unresolved=True)` and `--stop-unresolved`, a sham
drawn from another kind (`sham.kind`), `plan`'s line naming what no answers can
make a frame read, and the `egemma` battery's `"reasoning": true`, which needs
an eGemma newer than its v0.5.0.
