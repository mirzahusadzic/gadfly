# Upgrading

Each release that changes what a caller meets has a section here, the newest
first. In none of them does a verdict change: every kept run reads to the same
category. The site follows `main`, so a release not yet out says so.

Just after a release, PyPI can take a few minutes to list the new version,
and until then uv answers that it does not exist. Wait a few minutes, then
`--refresh-package midwife` makes uv look again, past its own cache.

---

### To 0.10.0, not yet released

On `main`, for the next release. No verdict changes, and this thing a caller
of 0.9.1 meets does:

| In 0.9.1 | In 0.10.0 | What to do |
| --- | --- | --- |
| A successor that added, changed or dropped a hole besides the one it filled asked the same question | `reframes` lists `holes`, and `gate` reads the successor as a reframing | Close only the hole the piece fills; a frame that takes in more is a new frame |

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
