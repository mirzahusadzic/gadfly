# Upgrading to 0.7.0

0.7.0 changes what the command line prints and how it ends, and how Gadfly
raises what it refuses. Verdicts do not change: every kept run reads to the
same category as in 0.6.0. This page lists what a caller of 0.6.0 meets, and
what to do.

0.7.1 changes nothing a caller meets: one test that read a refusal's message
now passes on Python 3.14 and later, as on 3.13.

---

### The command line

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

---

### JSON output

| Command | In 0.6.0 | In 0.7.0 |
| --- | --- | --- |
| any refusal with `--json` | `gadfly: <reason>` on standard error, as text | One object on standard error, `{"error": {"type", "exit", "message", "notes", "help"}}` |
| `run --json` | `stopped` and `openings` in its result | Its result also holds `exit`, and `warnings`, each with the status it gives |
| `check-frame --json` | `{"ok": false, ...}` on standard output for a refused frame | One `FrameError` object on standard error that lists `problems`, each with its notes; `{"ok": true, ...}` on standard output for an accepted one |

---

### Frames and Python callers

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
