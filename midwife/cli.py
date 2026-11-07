"""The command line: check-frame, plan, run, report, stats and portfolio,
and recoil's walk, successor, firm and gate.

    uv run gadfly plan examples/upgrade.json
    uv run gadfly run examples/upgrade.json \\
        --battery midwife.batteries.egemma:EGemma \\
        --calls 40 --out records.jsonl
    uv run gadfly report examples/upgrade.json records.jsonl
    uv run gadfly check-frame my-frame.json
    uv run gadfly portfolio a.json b.json

It uses only the public pipeline, and each command is a public function's
parity: what Python offers, a command does, and `--json` prints what the
function returns. `run` needs an explicit call budget,
writes each record as one JSON line the moment it exists, never writes over
a file and makes none when it is refused, and says when it stopped early;
`report` keeps a finding's evidence and its open obligations apart.
A battery is named `module:Class` and is imported from the current
directory.
"""

from __future__ import annotations

import argparse
import contextlib
import errno
import functools
import importlib
import io
import json
import os
import re
import shlex
import signal
import sys
import traceback
import warnings
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from . import __version__, errors, recoil, stats
from .errors import (
    BatteryError,
    FrameError,
    GadflyError,
    GadflyWarning,
    OpeningWarning,
    RecordsError,
    StoppedWarning,
    UsageError,
    noted,
    one_line,
    plain,
)
from .frame import schema
from .pipeline import (
    calls_needed,
    judge,
    overall,
    plan,
    run,
    situate,
    summed_usage,
    unthought,
)
from .portfolio import entry_from, summarize
from .types import Battery, Budget, Record
from .verdict import settled, unreachable
from .withhold import Withhold, read_withhold, refuse_withheld, withheld

EXAMPLES = """\
examples:
  gadfly check-frame my-frame.json      check a frame, with no call
  gadfly plan my-frame.json             its trials and their cost, with no call
  gadfly run my-frame.json --battery midwife.batteries.egemma:EGemma \\
      --calls 40 --out records.jsonl    make the calls, keeping each record
  gadfly report my-frame.json records.jsonl
                                        read the verdict, with no call
  gadfly walk frames/*.json --from frames/found.json --span slip
                                        where a piece climbs, with no call

docs: https://mirzahusadzic.github.io/gadfly/command-line
"""


def load_frame(path: str):
    """The frame in a JSON file, or on standard input for `-`, checked and
    hashed."""
    return situate(load_json(path, read_text(path, FrameError), FrameError))


def load_battery(spec: str):
    """An instance of the battery class `module:Class`."""
    module_name, sep, attribute = spec.partition(":")
    if not sep or not module_name or not attribute:
        raise UsageError("--battery is module:Class (for example midwife.batteries.egemma:EGemma)")
    if module_name.startswith("."):  # import_module raises TypeError on it, not ImportError
        raise BatteryError(
            f"module {module_name!r} could not be imported",
            "--battery names a module in full, not relative to another",
        )
    if os.getcwd() not in sys.path:  # as `python -m` would: your module, from here
        sys.path.insert(0, os.getcwd())
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:  # its words quoted: a battery's are not Gadfly's
        raise BatteryError(
            f"module {module_name!r} could not be imported", f"it said {str(error)!r}"
        ) from None
    except ValueError as error:  # a battery refuses with a ValueError, as in check
        if isinstance(error, GadflyError) and module_name.startswith("midwife."):
            raise  # a shipped battery's refusal, in Gadfly's own words
        raise BatteryError(
            f"battery {spec!r} could not be made", f"it said {str(error)!r}"
        ) from error
    target = getattr(module, attribute, None)
    if target is None:
        raise BatteryError(f"module {module_name!r} has no {attribute!r}")
    try:
        battery = target() if isinstance(target, type) else target
    except GadflyError as error:
        if module_name.startswith("midwife."):
            raise  # a shipped battery's refusal, in Gadfly's own words
        raise BatteryError(
            f"battery {spec!r} could not be made", f"it said {str(error)!r}"
        ) from None
    except (
        TypeError,
        ValueError,
        ImportError,
    ) as error:  # it needs arguments, refuses, or lacks a module
        raise BatteryError(
            f"battery {spec!r} could not be made", f"it said {str(error)!r}"
        ) from None
    if not isinstance(battery, Battery):
        raise BatteryError(
            f"{spec!r} is not a battery", "a battery has a name, check() and observe()"
        )
    return battery


def read_text(path: str, refusal: type[GadflyError]) -> str:
    """A file's text, or standard input's for `-`; text that is not UTF-8
    is a `refusal`."""
    if path == "-" and sys.stdin.isatty():  # nothing is piped in: say so rather than wait
        raise UsageError(
            "- reads standard input, which is a terminal", "pipe the file in, or name it"
        )
    try:
        if path != "-":
            return Path(path).read_text(encoding="utf-8")
        # stdin's own reader passes bad bytes on as surrogates: decode them here
        stream = getattr(sys.stdin, "buffer", None)
        if stream:
            return stream.read().decode("utf-8")
        text = sys.stdin.read()  # a caller's own text stream: no bytes beneath it
        text.encode("utf-8")  # a lone surrogate is a byte that was not UTF-8
        return text
    except (UnicodeDecodeError, UnicodeEncodeError):
        raise refusal(f"{_named(path)} is not UTF-8 text") from None


def load_json(path: str, text: str, refusal: type[GadflyError], line: int | None = None) -> Any:
    """`text` as JSON, or a `refusal` that names its file and where it
    broke; `line` is where `text` starts in the file, when it is one line."""
    at = f" at line {line}" if line else ""
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        where = f"line {(line or 1) + error.lineno - 1}, column {error.colno}"
        raise refusal(f"{_named(path)} is not JSON at {where} ({error.msg})") from None
    except RecursionError:  # deeper than Python reads
        raise refusal(f"{_named(path)} nests too deep to read{at}") from None
    except ValueError:  # a number past Python's limit on digits
        raise refusal(f"{_named(path)} holds a number too long to read{at}") from None


def read_bytes(path: str) -> bytes:
    """A file's bytes, or standard input's for `-`, as they are: what a
    file's SHA-256 is taken of."""
    if path == "-" and sys.stdin.isatty():  # nothing is piped in: say so rather than wait
        raise UsageError(
            "- reads standard input, which is a terminal", "pipe the file in, or name it"
        )
    if path != "-":
        return Path(path).read_bytes()
    stream = getattr(sys.stdin, "buffer", None)
    # a caller's own text stream: a lone surrogate stays a byte no UTF-8 reader takes
    return stream.read() if stream else sys.stdin.read().encode("utf-8", "surrogatepass")


def _named(path: str) -> str:
    return "standard input" if path == "-" else f"file {path!r}"


def _shell(path: str) -> str:
    # a path as a shell would take it back, or Python's repr where that would
    # break a line, as shlex keeps a line break inside its quotes
    return shlex.quote(path) if one_line(path) else repr(path)


def load_records(path: str) -> list[dict[str, Any]]:
    """The records kept in a JSON Lines file, or on standard input for `-`."""
    return [record for _, record in _numbered(path)]


def _numbered(path: str) -> list[tuple[int, dict[str, Any]]]:
    # each record with the line it was read from, for a refusal to point at
    # a record ends at a newline only: U+2028 and its kind are text inside it
    lines = [line.removesuffix("\r") for line in read_text(path, RecordsError).split("\n")]
    return [
        (n, load_json(path, text, RecordsError, n))
        for n, text in enumerate(lines, 1)
        if text.strip()
    ]


def render_report(frame, records: list[dict[str, Any]]) -> str:
    """The person-readable report: the overall category, then each input's
    levels, evidence and open obligations, each on its own line."""
    findings = judge(frame, records)
    combined = overall(findings)
    unasked = _settled_calls(frame, records)
    rows = [
        f"frame: {plain(frame.name)} ({frame.hash})",
        f"records: {len(records)} of {calls_needed(frame)} planned calls"
        + (f"; {unasked} missing, none able to change a level" if unasked else ""),
        f"overall: {combined.category}",
    ]
    rows.extend(f"  {line}" for line in combined.evidence)
    rows.extend(f"  obligation: {line}" for line in combined.obligations)
    for finding in findings:
        rows.append(f"{finding.input}: {finding.category}")
        rows.extend(f"  level {trial}: {level}" for trial, level in finding.levels.items())
        rows.extend(f"  evidence: {line}" for line in finding.evidence)
        rows.extend(f"  obligation: {line}" for line in finding.obligations)
    return "\n".join(rows)


def _settled_calls(frame, records: list[dict[str, Any]]) -> int:
    # the calls missing from settled trials: what the records show, not why
    # they are missing; under stable the baseline and repeat never settle short
    whole = {"baseline", "repeat"} if frame.raw["standing"].get("stable") else set()
    seen: dict[tuple[str, str], list[str | None]] = defaultdict(list)
    for record in records:
        seen[record["input"], record["trial"]].append(record["observation"])
    return sum(
        frame.quorum - len(answers)
        for (_, trial), answers in seen.items()
        if len(answers) < frame.quorum
        and trial not in whole
        and settled(answers, frame.quorum, frame.agree, frame.labels)
    )


def _change(frame, trial) -> str:
    # what a trial does to the body, so predictions can be written from here
    if trial.kind == "inversion":
        return "inverts " + ", ".join(f"{plain(a)} to {plain(b)}" for a, b in trial.renamed)
    if trial.kind == "input-inversion":
        return "inverts the input's " + ", ".join(
            f"{plain(a)} to {plain(b)}" for a, b in trial.renamed
        )
    if trial.renamed:
        return "renames " + ", ".join(f"{plain(a)} to {plain(b)}" for a, b in trial.renamed)
    if trial.kind == "placement":
        move = frame.interventions["placement"]
        return f"moves {move['span']} after {move['after']}"
    if trial.removed:
        return "cuts " + ", ".join(trial.removed) if len(trial.spans) else "cuts every span"
    return "nothing, asked again" if trial.kind == "repeat" else "nothing"


def command_plan(args) -> int:
    """`gadfly plan`: the trials, what each changes, and the call count,
    without a call; with --most or --runs, also the most calls asking the
    frame until firm can make (`midwife.recoil.calls_until_firm`)."""
    frame = load_frame(args.frame)
    trials = plan(frame)
    body = {
        "frame": frame.name,
        "hash": frame.hash,
        "calls": calls_needed(frame),
        "inputs": len(frame.inputs),
        "quorum": frame.quorum,
        "trials": [
            {
                "id": trial.id,
                "kind": trial.kind,
                "removed": list(trial.removed),
                "renamed": [list(pair) for pair in trial.renamed],
                "change": _change(frame, trial),
                "body": trial.body_hash,
            }
            for trial in trials
        ],
        "unreachable": unreachable(frame),
    }
    power = None if args.agreement is None else stats.power(frame, args.agreement)
    if power is not None:
        body["power"] = power.as_dict()
    climb = _climb(args, frame)
    if climb is not None:
        body["climb"] = climb
    if args.json:
        print(json.dumps(body, indent=2))
    else:
        print(f"{plain(body['frame'])} ({body['hash']}): {body['calls']} calls")
        if power is not None:
            print(f"power: {_powered(power)}")
        if climb is not None:
            more = climb["most"] - climb["kept"]
            runs = f"{more} more run{'s' * (more != 1)} of {body['calls']} calls"
            kept = f"{climb['kept']} kept of {climb['most']} at most"
            print(f"until firm: at most {climb['calls']} calls, {runs}, {kept}")
        for trial in trials:
            print(f"  {trial.id:12} body {trial.body_hash[:12]}  {_change(frame, trial)}")
        if body["unreachable"] is None:
            print("too many answers to read which categories it can reach")
        for category, held in (body["unreachable"] or {}).items():
            stay_open = bool(held) and not frame.outside_scope  # an exclusion is no check
            print(f"never {category}, whatever the answers" + (": these stay open" * stay_open))
            print("".join(f"  {line}\n" for line in held), end="")
    return 0


def _percent(share: float) -> str:
    return f"{round(100 * share)}%"


def _parts(shares: dict[str, float]) -> str:
    # shares of a whole, as whole percents that add up to 100 (largest
    # remainders), a share too small for one percent said as under 1%
    exact = {key: 100 * share for key, share in shares.items()}
    whole = {key: int(value) for key, value in exact.items()}
    short = round(sum(exact.values())) - sum(whole.values())
    for key in sorted(exact, key=lambda key: exact[key] - whole[key], reverse=True)[:short]:
        whole[key] += 1
    return ", ".join(
        f"{plain(key)} {whole[key]}%" if whole[key] else f"{plain(key)} under 1%" for key in exact
    )


def _powered(power: stats.Power) -> str:
    # one line: what the quorum can resolve at the reader's agreement
    return (
        f"at {_percent(power.agreement)} agreement, a trial reaches a level of "
        f"{power.agree} of {power.quorum} {_percent(power.trial)} of the time, and all "
        f"{power.trials} trials the plan asks of an input {_percent(power.input)}"
    )


def command_stats(args) -> int:
    """`gadfly stats`: how firm each trial's answers are over the kept runs,
    whether each trial moved the baseline's answer, how likely the quorum was
    to reach a level, and how often each run's verdict comes out the same
    when its calls are drawn again. No verdict changes."""
    frame = load_frame(args.frame)
    runs = [load_records(path) for path in args.records]
    others = [(load_frame(other), load_records(records)) for other, records in args.pool or []]
    extra = stats.pooled(frame, others)
    stats.require_runs([*runs, extra])
    compared = stats.compare(frame, runs, extra)
    measured = stats.agreement(runs)
    power = None if measured is None else stats.power(frame, measured)
    verdicts = stats.observed(frame, runs)
    shares = stats.stability(frame, runs, args.resamples) if args.resamples else []
    calls = sum(len(records) for records in runs)
    if args.json:
        body = {
            "frame": frame.name,
            "hash": frame.hash,
            "runs": args.records,
            "calls": calls,
            "pooled": len(extra),
            "agreement": measured,
            "power": None if power is None else power.as_dict(),
            "inputs": {x: [row.as_dict() for row in rows] for x, rows in compared.items()},
            "verdicts": verdicts,
            "resamples": args.resamples,
            "stability": shares,
        }
        print(json.dumps(body, indent=2))
        return 0
    pooled = f", and {len(extra)} calls pooled from {len(others)} other frames" if extra else ""
    print(f"frame: {plain(frame.name)} ({frame.hash})")
    print(f"records: {len(runs)} run{'s' * (len(runs) != 1)}, {calls} calls{pooled}")
    if measured is not None:
        print(
            f"agreement: {_percent(measured)} of calls give their trial's most common answer "
            "in their own run"
        )
        print(f"power: {_powered(power)}")
    elif calls:
        print("agreement: no trial was asked twice in a run, so there is no repeat to measure")
    for x, rows in compared.items():
        print(f"input {plain(x)}")
        for row in rows:
            given = [f"{plain(label)} {n}" for label, n in row.answers.items()]
            if row.openings:  # apart from the labels: a label may be named "opening"
                given.append(f"{row.openings} opening{'s' * (row.openings != 1)}")
            answers = ", ".join(given)
            line = (
                f"  {row.trial:13} {row.calls:3} calls  {answers}  top {_percent(row.share)} "
                f"({_percent(row.low)}-{_percent(row.high)})"
            )
            if row.differ is not None:
                line += f", at most {_percent(row.differ)} differ from {plain(row.baseline)}"
            elif row.moved is not None:
                line += (
                    f", p {row.moved:.2g} against {plain(row.baseline)} (Holm {row.adjusted:.2g})"
                )
            print(line)
    if shares:
        print(f"verdicts, each run's calls drawn again {args.resamples} times")
    redrawn = shares or [{}] * len(verdicts)
    for place, (found, drawn) in enumerate(zip(verdicts, redrawn, strict=True), 1):
        for x, category in found.items():
            again = _parts(drawn[x]) if drawn.get(x) else ""
            if again:
                again = f"; drawn again {again}"
            elif shares:  # its trials were each asked once: a draw is the run itself
                again = "; each trial asked once, nothing to draw again"
            print(f"  run {place}, {plain(x)}  {category}{again}")
    return 0


def command_run(args) -> int:
    """`gadfly run`: every planned call the budget covers, each record kept."""
    frame = load_frame(args.frame)
    withhold = _withhold(args)
    if args.calls == "auto":  # a whole run's calls, the most any run of it makes
        args.calls = calls_needed(frame)
    battery = load_battery(args.battery)
    numbered = _numbered(args.kept) if args.kept else []
    kept = [old for _, old in numbered]
    for line, old in numbered:  # the new file starts with them: found out before a call
        try:
            json.dumps(old, ensure_ascii=False).encode("utf-8")
        except UnicodeEncodeError:
            raise RecordsError(
                f"{_named(args.kept)} holds a lone surrogate at line {line}",
                "no file can hold it; correct or drop that record, then run again",
            ) from None
    out = Path(args.out)
    streamed = args.out == "-"  # the records own standard output; the rest is a message
    if streamed and args.json:
        raise UsageError(
            "--json and --out - both print to standard output", "choose a file for --out"
        )
    if not streamed:
        _new_file(
            out, "kept records are never written over; choose a new --out, or finish it with --kept"
        )
    # a path as a shell would take it back, so a colon or a space in it breaks no line
    where, say = ("standard output", sys.stderr) if streamed else (_shell(str(out)), sys.stdout)

    def opened():
        return sys.stdout if streamed else out.open("x", encoding="utf-8")

    files = []  # the file is made by the first record, so a refused run leaves none
    made = []
    # a run takes minutes: in a terminal, count the calls as they are made
    progress = sys.stderr.isatty() and not args.json

    def keep(record: Record) -> None:
        line = json.dumps(record.as_dict(), ensure_ascii=False) + "\n"  # before any file is made
        if not files:
            files.append(opened())
            for old in kept:  # the kept records first, so the new file is the whole run
                files[0].write(json.dumps(old, ensure_ascii=False) + "\n")
        files[0].write(line)
        files[0].flush()
        made.append(record)
        if progress:
            print(f"\r{len(made)} calls made", end="", file=sys.stderr, flush=True)

    try:
        with warnings.catch_warnings(record=True) as caught:  # said below, as refusals are
            warnings.simplefilter("always", GadflyWarning)
            result = run(
                frame,
                battery,
                Budget(args.calls, args.output_tokens, args.token_budget),
                on_record=keep,
                only=args.only,
                kept=kept,
                settle=args.settle,
                stop_unresolved=args.stop_unresolved,
                parallel=args.parallel,
                withhold=withhold,
            )
    except KeyboardInterrupt as interrupt:
        # every record made so far is already in its file: say how to finish
        stopped = f"stopped by Ctrl-C after {len(made)} calls"
        if not files:
            said = noted(KeyboardInterrupt(f"{stopped}, and no record was kept"))
        elif streamed:
            said = noted(
                KeyboardInterrupt(f"{stopped}; they went to standard output"),
                "finish with them as --kept and a new --out",
            )
        else:
            said = noted(
                KeyboardInterrupt(f"{stopped}; they are in file {str(out)!r}"),
                f"finish with --kept {str(out)!r} and a new --out",
            )
        openings = Counter(r.opening for r in made if r.opening is not None)
        if openings:  # nothing passes in silence, a Ctrl-C's calls included
            reason, _ = openings.most_common(1)[0]
            many = sum(openings.values())
            said.add_note(f"{many} of them came back as openings, most often {reason!r}")
        said.running = getattr(interrupt, "running", 0)  # calls hung, left to their threads
        if said.running:
            said.add_note(f"{said.running} calls still out were left unanswered")
        raise said from None
    finally:
        if not streamed:
            for file in files:
                file.close()
        if progress and made:
            print(file=sys.stderr)
    if not result.records and result.stopped:  # nothing was spent: a refusal, not a run
        raise UsageError(
            result.stopped,
            "gadfly plan shows the calls a whole run needs"
            if result.stopped.startswith("the plan needs")
            else "--token-budget must cover one call's --output-tokens",
        )
    for warning in caught:  # any other code's warning, shown as Python would
        if not issubclass(warning.category, GadflyWarning):
            warnings.showwarning(
                warning.message, warning.category, warning.filename, warning.lineno
            )
    if not files:  # nothing was left to ask: the new file, empty or kept, is still the whole run
        files.append(opened())
        files[0].writelines(json.dumps(old, ensure_ascii=False) + "\n" for old in kept)
        if not streamed:
            files[0].close()
    # a service that is down answers every call with an opening: say so, so a
    # run that spent its calls on nothing does not read as a finished one
    openings = Counter(r.opening for r in result.records if r.opening is not None)
    # and a run its budget cut short, so its records do not read as the whole run
    status = (
        1
        if result.records and sum(openings.values()) == len(result.records)
        else 3
        if result.stopped
        else 0
    )
    # what the run did not do as asked: its warnings, with what to do, and the
    # status each gives (an OpeningWarning gives 1 only when every call opened)
    raised = []
    for warning in (w.message for w in caught if issubclass(w.category, GadflyWarning)):
        gives = warning.exit
        if isinstance(warning, OpeningWarning):
            gives = OpeningWarning.exit if status == OpeningWarning.exit else 0
            if gives:
                warning.add_note("nothing was read; run again into a new file once it answers")
        if isinstance(warning, StoppedWarning):
            kept_as = "them" if streamed else repr(str(out))
            warning.add_note(f"finish with --kept {kept_as} and a new --out")
        raised.append((warning, gives))
    if args.json:  # one document: the run, and its warnings within it
        payload = {
            "frame": frame.name,
            "hash": frame.hash,
            "out": str(out),
            "planned": result.planned,
            "made": len(result.records),
            "usage": summed_usage(result.records),
            "unthought": unthought(result.records),
            "kept": len(kept) if files else 0,
            "settled": result.settled,
            "unasked": result.unasked,
            "stopped": result.stopped,
            "openings": dict(openings.most_common()),
            "exit": status,
            "warnings": [described(warning, gives) for warning, gives in raised],
        }
        print(json.dumps(payload, indent=2))
    else:
        before = (
            f", after {len(kept)} kept record{'s' * (len(kept) != 1)}" if kept and files else ""
        )
        print(f"wrote {len(result.records)}/{result.planned} calls to {where}{before}", file=say)
        if result.settled:
            print(
                f"settled: {result.settled} calls not made, their trials' levels already fixed",
                file=say,
            )
        if result.unasked:
            print(
                f"unasked: {result.unasked} calls not made, "
                "their input unresolved whatever they gave",
                file=say,
            )
        read = (
            f"pipe them to gadfly report {_shell(args.frame)} -"
            if streamed
            else f"gadfly report {_shell(args.frame)} {where}"
        )
        print(f"to read the verdict: {read}", file=say)
        for warning, _ in raised:
            notes = list(getattr(warning, "__notes__", []))
            print(f"{type(warning).__name__}: {warning}", *notes, sep="\n", file=sys.stderr)
    return status


def _new_file(out: Path, exists: str) -> None:
    # a new file for --out: never another's, nor what a link, even a broken
    # one, points at, in a folder that can be written; found out before a call
    if out.is_dir() and not out.is_symlink():
        raise noted(
            IsADirectoryError(f"{str(out)!r} is a folder, not a file"),
            "name a new file in it, or choose another --out",
        )
    if os.path.lexists(out):
        raise noted(FileExistsError(f"file {str(out)!r} exists already"), exists)
    if out.parent.exists() and not out.parent.is_dir():
        raise noted(
            NotADirectoryError(f"path {str(out)!r} runs through a file, not a folder"),
            "choose another --out",
        )
    if not out.parent.is_dir():
        raise noted(
            FileNotFoundError(f"folder {str(out.parent)!r} does not exist"),
            "make it, or choose another --out",
        )
    if not os.access(out.parent, os.W_OK):
        raise noted(
            PermissionError(f"folder {str(out.parent)!r} cannot be written"),
            "choose another --out",
        )


def command_report(args) -> int:
    """`gadfly report`: the verdict read from a kept JSON Lines file."""
    frame = load_frame(args.frame)
    records = load_records(args.records)
    if args.json:
        findings = judge(frame, records)
        document = {
            "frame": frame.name,
            "hash": frame.hash,
            "records": len(records),
            "usage": summed_usage(records),
            "unthought": unthought(records),
            "overall": overall(findings).as_dict(),
            "findings": [finding.as_dict() for finding in findings],
        }
        print(json.dumps(document, indent=2))
    else:
        print(render_report(frame, records))
    return 0


def command_check_frame(args) -> int:
    """`gadfly check-frame`: the frame's shape against the schema (when
    jsonschema is installed), then the parser's authoritative refusal, and
    with --withhold, any prompt holding text the set withholds, every part
    read, since no battery is named."""
    withhold, frame = _withhold(args), None
    try:
        raw = load_json(args.frame, read_text(args.frame, FrameError), FrameError)
    except FrameError as error:  # not text or not JSON: one problem, and nothing more to check
        notes = list(getattr(error, "__notes__", []))
        raw, checked, problems = None, "JSON", [{"at": "/", "problem": str(error), "notes": notes}]
    else:
        checked, problems = "parser", []
    if raw is not None:
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            pass
        else:
            checked = "schema and parser"
            try:  # sorted by where and what, never by the whole instance printed
                found = sorted(
                    Draft202012Validator(schema()).iter_errors(raw),
                    key=lambda error: ([str(part) for part in error.absolute_path], error.message),
                )
            except RecursionError:  # deeper than the schema's checker reads: the parser says so
                found = []
            for error in found:
                where = "/" + "/".join(str(part) for part in error.absolute_path)
                problems.append({"at": where, "problem": error.message, "notes": []})
        try:
            frame = situate(raw)
        except FrameError as error:
            notes = list(getattr(error, "__notes__", []))
            frame, problems = None, [*problems, {"at": "/", "problem": str(error), "notes": notes}]
    held = [] if frame is None or withhold is None else withheld(frame, withhold)
    if held:
        try:
            refuse_withheld(frame, withhold)
        except FrameError as error:
            notes = list(getattr(error, "__notes__", []))
            problems.append({"at": "/", "problem": str(error), "notes": notes})
    if problems and args.json:  # one FrameError, as every refusal is, listing them all
        said = {"type": "FrameError", "exit": FrameError.exit, "message": problems[0]["problem"]}
        said |= {"notes": problems[0]["notes"], "help": f"{TROUBLESHOOTING}#frameerror"}
        said |= {"checked": checked, "problems": problems}
        if withhold is not None:
            said["withheld"] = [place.as_dict() for place in held]
        print(json.dumps({"error": said}, indent=2), file=sys.stderr)
    elif problems:  # each a FrameError, gathered rather than raised at the first
        for problem in problems:
            at = "" if problem["at"] == "/" else f" at {problem['at']}"
            print(
                f"FrameError: {problem['problem']}{at}",
                *problem["notes"],
                sep="\n",
                file=sys.stderr,
            )
    elif args.json:
        result = {"ok": True, "checked": checked, "problems": []}
        result.update(frame=frame.name, hash=frame.hash, calls=calls_needed(frame))
        if withhold is not None:
            result["withheld"] = []
        print(json.dumps(result, indent=2))
    else:
        print(f"ok ({checked}): {plain(frame.name)} ({frame.hash}), {calls_needed(frame)} calls")
    return FrameError.exit if problems else 0


def _calls(text: str) -> int | str:
    # --calls: a whole number, or auto for what the frame itself needs; any
    # other value is refused in argparse's own words for a whole number
    return text if text == "auto" else int(text)


_calls.__name__ = "int"


def _withhold(args) -> Withhold | None:
    # the withhold set --withhold names, read before anything is asked
    path = getattr(args, "withhold", None)
    return None if path is None else read_withhold(read_bytes(path), path=path)


def command_portfolio(args) -> int:
    """`gadfly portfolio`: several reports counted side by side."""
    documents = [
        load_json(path, read_text(path, RecordsError), RecordsError) for path in args.reports
    ]
    summary = summarize([entry_from(document) for document in documents])
    if args.json:
        print(json.dumps(summary, indent=2))
        return 0
    print(f"{summary['frames']} frame{'s' * (summary['frames'] != 1)}")
    for category, names in summary["by_category"].items():
        print(f"{category}: {', '.join(map(plain, names))}")
    if summary["shared_obligations"]:
        print("open in several frames:")
        for obligation, names in summary["shared_obligations"].items():
            print(f"  {plain(obligation)} ({', '.join(map(plain, names))})")
    if summary["input_disagreements"]:
        print("frames whose inputs disagree:")
        for name, inputs in summary["input_disagreements"].items():
            print(f"  {plain(name)}: " + ", ".join(f"{plain(x)} {c}" for x, c in inputs.items()))
    return 0


# a run kept in a --runs folder: one JSON Lines file, named by its place
RUN_FILE = re.compile(r"([1-9][0-9]*)\.jsonl")


def _which(frame) -> dict[str, str]:
    # a frame as a JSON document names it, as every command's names its frame
    return {"frame": frame.name, "hash": frame.hash}


def _short(frame) -> str:
    # a frame as a line names it: its name and the start of its hash, since a
    # successor keeps the name of the frame it succeeds
    return f"{plain(frame.name)} ({frame.hash[:12]})"


def _piece_document(piece) -> dict[str, str]:
    return {"text": piece.text, "kind": piece.kind, "sha256": piece.sha256}


def _piece(args):
    # the frame --from names, and the piece found in it: one of its spans
    # (--span), or its decision read as a label (--decision); or, for
    # successor, a text found in no frame given (--text), of the --kind named
    text, kind = getattr(args, "text", None), getattr(args, "kind", None)
    if text is not None:
        if args.source is not None:
            raise UsageError(
                "--from and --text cannot be given together",
                "a piece is a text of its own, or one found in the frame --from names",
            )
        if kind is None:
            raise UsageError("missing --kind", "a --text piece fills only a hole of its own kind")
        return None, recoil.Piece(text, kind)
    if kind is not None:
        raise UsageError(
            "--kind is given without --text",
            "a piece found in a frame is of its span's kind, or the kind its frame offers",
        )
    if args.source is None:
        raise UsageError("missing --from", "name the frame the piece was found in")
    source = load_frame(args.source)
    if args.span is not None:
        return source, recoil.found(source, args.span)
    return source, recoil.decided(source, args.decision)


def _set(key: str, value: str) -> tuple[str, Any]:
    # a key the successor sets, its value given as JSON
    try:
        return key, json.loads(value)
    except (ValueError, RecursionError):
        raise UsageError(
            f"--set {key!r} is given {value!r}, which is not JSON",
            "give the value as JSON, quoted for the shell",
        ) from None


def _bounds(args) -> None:
    # how firm is firm, and how many runs are read, as until_firm takes them
    if not 0 < args.firm <= 1:  # NaN included: it is no share
        raise UsageError("--firm is a share above 0, up to 1")
    if args.most is not None:
        _most(args.most)


def _most(most: int) -> None:
    if most < 1:
        raise UsageError("--most is a whole number of runs, at least 1")


def _climb(args, frame) -> dict[str, int] | None:
    # the most calls asking a frame until firm can make, counted as firm
    # would ask it: --most runs at most, those --runs keeps counted as made
    if args.most is None and args.runs is None:
        return None
    if args.most is not None:
        _most(args.most)
    most = recoil.most_of(frame, args.most)
    kept = []
    if args.runs is not None:
        missing = "name the folder gadfly firm keeps the frame's runs in"
        folder = _runs_folder(args.runs, missing, write=False)
        kept = [records for _, _, records in _kept_runs(folder, frame, most)]
    calls = recoil.calls_until_firm(frame, kept=kept, most=most)
    return {"most": most, "kept": len(kept), "calls": calls}


def _runs_folder(path: str, missing: str, write: bool) -> Path:
    # the folder --runs names: one that exists, and, to keep new runs, can be written
    folder = Path(path)
    if folder.exists() and not folder.is_dir():
        raise noted(
            NotADirectoryError(f"{str(folder)!r} is a file, not a folder"),
            "--runs names the folder that keeps the frame's runs",
        )
    if not folder.is_dir():
        raise noted(FileNotFoundError(f"folder {str(folder)!r} does not exist"), missing)
    if write and not os.access(folder, os.W_OK):
        raise noted(
            PermissionError(f"folder {str(folder)!r} cannot be written"), "choose another --runs"
        )
    return folder


def _kept_runs(folder: Path, frame, most: int) -> list[tuple[int, Path, list[dict[str, Any]]]]:
    # the runs a folder keeps, each a file named by its place, 1.jsonl, 2.jsonl
    # and on, read in that order; each a whole run, and any other file left alone
    named = sorted(
        (int(match[1]), path)
        for path in folder.iterdir()
        if (match := RUN_FILE.fullmatch(path.name)) and path.is_file()
    )
    many = len(named)
    if many > most:
        raise UsageError(
            f"folder {str(folder)!r} keeps {many} runs, more than --most reads",
            "move the earliest runs out"
            if recoil.declared_most(frame) is not None
            else "raise --most, or move the earliest runs out",
        )
    each, kept = calls_needed(frame), []
    for place, path in named:
        records = load_records(str(path))
        many = len(records)
        if many != each:
            raise RecordsError(
                f"file {str(path)!r} holds {many} of a run's {each} calls",
                "a run cut short is never read as firm; move it out of the folder",
            )
        kept.append((place, path, records))
    return kept


def command_walk(args) -> int:
    """`gadfly walk`: where a piece climbs from the frame it was found in, up
    through the frames given, without a call (`midwife.recoil.walk`); with
    --made, through the artefacts a crossing's records say it made; with
    --sideways, one step aside to the siblings of the frame it starts from; with
    --vectors, its fits ordered by cosine; with --calls, which fits that
    many calls cover, each until firm."""
    if args.space is not None and args.vectors is None:  # what it is asked, before any file
        raise UsageError(
            "--space is given without --vectors",
            "--space names the space to order by, among the vectors --vectors gives",
        )
    if args.most is not None:
        if args.calls is None:
            raise UsageError(
                "--most is given without --calls",
                "--most counts the runs each fit may take against the calls --calls gives",
            )
        _most(args.most)
    if args.calls is not None and args.calls < 1:
        raise UsageError("a walk's budget is a whole number of calls, at least 1")
    source, piece = _piece(args)
    frames = [load_frame(path) for path in args.frames]
    made = [load_records(path) for path in args.made or []]
    vectors = None
    if args.vectors is not None:
        vectors = recoil.read_vectors(read_bytes(args.vectors), path=args.vectors)
    most = recoil.MOST if args.most is None else args.most
    walked = recoil.walk(
        piece,
        source,
        frames,
        made=made,
        sideways=args.sideways,
        vectors=vectors,
        space=args.space,
        calls=args.calls,
        most=most,
    )

    aside = {sibling.hash for sibling in walked.siblings}

    def reached(frame) -> dict[str, Any]:  # a frame, and how the walk reached it
        pairs = walked.made.get(frame.hash, ())
        made = [{"trial": t, "input": x} for t, x in pairs]
        return {**_which(frame), "sideways": frame.hash in aside, "made": made}

    def through(frame) -> str:
        pairs = walked.made.get(frame.hash, ())
        said = ", ".join(f"{trial} for {input_}" for trial, input_ in pairs)
        how = ", sideways" if frame.hash in aside else ""
        return f"{how}, through the artefact made in {said}" if pairs else how

    if args.json:
        document = {
            "piece": {**_piece_document(piece), "from": _which(source)},
            "fits": [{**reached(frame), "holes": list(holes)} for frame, holes in walked.fits],
            "order": [
                {
                    **reached(fit.frame),
                    "hole": fit.hole,
                    "cosine": fit.cosine,
                    "unordered": fit.unordered,
                    "calls": fit.calls,
                    "asked": fit.asked,
                }
                for fit in walked.order
            ],
            "deferred": [
                {**reached(frame), "holes": list(holes)} for frame, holes in walked.deferred
            ],
            "passed": [reached(frame) for frame in walked.passed],
            "frontier": list(walked.frontier),
            "complete": walked.complete,
            "budget": walked.budget,
            "most": walked.most,
            "space": walked.space,
            "vectors": walked.vectors,
        }
        print(json.dumps(document, indent=2))
        return 0
    print(f"piece: {piece.text!r}, of kind {plain(piece.kind)}, from {_short(source)}")
    for fit in walked.order:
        near = "" if fit.cosine is None else f", cosine {fit.cosine:.4f}"
        kept = "" if fit.unordered is None else f", kept in its place, {fit.unordered}"
        counted = "" if fit.calls is None else f", at most {fit.calls} calls until firm"
        unasked = ", not asked, past the budget" if fit.asked is False else ""
        line = f"fits: {_short(fit.frame)}, hole {fit.hole}{through(fit.frame)}"
        print(f"{line}{near}{kept}{counted}{unasked}")
    for frame, holes in walked.deferred:
        held = f"hole {', '.join(holes)}{through(frame)}"
        print(f"deferred: {_short(frame)}, {held}, kept and not asked")
    for frame in walked.passed:
        print(f"passed: {_short(frame)}{through(frame)}")
    for text in walked.frontier:
        print(f"frontier: {text}, quoted by a frame and held by none given")
    print(f"complete: {'yes' if walked.complete else 'no'}")
    if walked.space is not None:
        print(f"ordered: by cosine in space {plain(walked.space)}, vectors {walked.vectors}")
    if walked.budget is not None:
        asked, budget, most = [fit for fit in walked.order if fit.asked], walked.budget, walked.most
        calls = f"{budget} call{'s' * (budget != 1)} cover{'s' * (budget == 1)}"
        covered = f"{len(asked)} fit{'s' * (len(asked) != 1)} of {len(walked.order)}"
        spent = sum(fit.calls for fit in asked)
        spent = f", at most {spent} call{'s' * (spent != 1)} in all" if asked else ""
        print(f"budget: {calls} {covered}{spent}, each fit at most {most} run{'s' * (most != 1)}")
    return 0


def command_successor(args) -> int:
    """`gadfly successor`: the frame a fit is asked again as, its hole filled
    with the piece (`midwife.recoil.successor`), checked as any frame is and
    written to standard output or a new file, never over one."""
    frame = load_frame(args.frame)
    source, piece = _piece(args)
    changes = dict(_set(key, value) for key, value in args.set or [])
    draft = recoil.successor(frame, args.hole, piece, after=args.after, **changes)
    try:
        after = situate(draft)
    except FrameError as error:
        error.add_note(f"the successor of frame {frame.name!r} is checked as any frame is")
        raise
    out = None if args.out == "-" else Path(args.out)
    text = json.dumps(draft, indent=2, ensure_ascii=False) + "\n"  # as an author writes a frame
    if out is not None:
        _new_file(out, "a frame is never written over; choose a new --out")
        with out.open("x", encoding="utf-8") as file:
            file.write(text)
    changed = recoil.reframes(frame, after)
    if args.json:  # one document, the draft within it
        document = {
            **_which(after),
            "of": _which(frame),
            "hole": args.hole,
            "after": args.after,
            "piece": {**_piece_document(piece), "from": None if source is None else _which(source)},
            "reframes": changed,
            "out": None if out is None else str(out),
            "draft": draft,
        }
        print(json.dumps(document, indent=2))
        return 0
    if out is None:  # the frame owns standard output; the rest is a message
        sys.stdout.write(text)
    say = sys.stderr if out is None else sys.stdout
    placed = "" if args.after is None else f", after span {args.after}"
    filled = f"its hole {args.hole} filled{placed}"
    print(f"successor: {_short(after)}, of {_short(frame)}, {filled}", file=say)
    if changed:
        asks = "so it asks another question, read against no category"
        print(f"reframes: {', '.join(changed)}, {asks}", file=say)
    else:
        print("reframes: nothing, so it asks the same question, read from its own runs", file=say)
    if out is not None:
        print(f"wrote it to {_shell(str(out))}", file=say)
    return 0


def command_firm(args) -> int:
    """`gadfly firm`: ask a frame one whole run at a time until its verdict is
    firm (`midwife.recoil.until_firm`). The runs --runs keeps count as runs
    made, and each new run is kept there as a new file, record by record."""
    frame = load_frame(args.frame)
    withhold = _withhold(args)
    _bounds(args)
    most = recoil.most_of(frame, args.most)
    folder = _runs_folder(args.runs, "make it, or choose another --runs", write=True)
    kept = _kept_runs(folder, frame, most)
    each = calls_needed(frame)
    if args.calls == "auto":  # the most asking until firm can make, beyond the kept runs
        made_by = [records for _, _, records in kept]
        args.calls = max(1, recoil.calls_until_firm(frame, kept=made_by, most=most))
    if not kept and args.calls < each:  # nothing to read and nothing to ask: refused, as run's
        raise UsageError(
            f"a run needs {each} calls; --calls allows {args.calls}",
            "gadfly plan shows the calls a run needs",
        )
    battery = load_battery(args.battery)
    # a new run's file comes after every name a run could hold, a folder's too
    last = max(
        (int(match[1]) for path in folder.iterdir() if (match := RUN_FILE.fullmatch(path.name))),
        default=0,
    )
    files = []  # a run's file is made by its first record, so a refusal leaves none
    made = []
    progress = sys.stderr.isatty() and not args.json

    def keep(record: Record) -> None:
        line = json.dumps(record.as_dict(), ensure_ascii=False) + "\n"  # before any file is made
        if len(made) % each == 0:  # a run's first record: its own file, after the last
            if files:
                files[-1].close()
            files.append((folder / f"{last + len(files) + 1}.jsonl").open("x", encoding="utf-8"))
        files[-1].write(line)
        files[-1].flush()
        made.append(record)
        if progress:
            print(f"\r{len(made)} calls made", end="", file=sys.stderr, flush=True)

    try:
        with warnings.catch_warnings(record=True) as caught:  # said below, as refusals are
            warnings.simplefilter("always", GadflyWarning)
            asked = recoil.until_firm(
                frame,
                battery,
                Budget(args.calls, args.output_tokens, args.token_budget),
                kept=[records for _, _, records in kept],
                firm=args.firm,
                most=most,
                on_record=keep,
                parallel=args.parallel,
                withhold=withhold,
            )
    except KeyboardInterrupt:
        # every record made so far is already in its file: say which run is cut short
        stopped = f"stopped by Ctrl-C after {len(made)} calls"
        if not files:
            said = noted(KeyboardInterrupt(f"{stopped}, and no record was kept"))
        elif len(made) % each:
            said = noted(
                KeyboardInterrupt(f"{stopped}; the run cut short is in file {files[-1].name!r}"),
                "a run cut short is never read as firm; move it out of the folder",
            )
        else:
            said = noted(KeyboardInterrupt(f"{stopped}; each run made is whole and kept"))
        raise said from None  # one call at a time: none is left out in a thread
    finally:
        for file in files:
            file.close()
        if progress and made:
            print(file=sys.stderr)
    for warning in caught:  # any other code's warning, shown as Python would
        if not issubclass(warning.category, GadflyWarning):
            warnings.showwarning(
                warning.message, warning.category, warning.filename, warning.lineno
            )
    openings = Counter(r.opening for r in made if r.opening is not None)
    status = 1 if made and sum(openings.values()) == len(made) else 3 if asked.stopped else 0
    raised = []
    for warning in (w.message for w in caught if issubclass(w.category, GadflyWarning)):
        gives = warning.exit
        if isinstance(warning, OpeningWarning):
            gives = OpeningWarning.exit if status == OpeningWarning.exit else 0
            if gives:
                warning.add_note("nothing was read; ask again once it answers")
        if isinstance(warning, StoppedWarning):
            warning.add_note(
                f"the run cut short is in file {files[-1].name!r}; move it out of the folder"
                if len(made) % each
                else "raise --calls or --token-budget, and ask again with the same --runs"
            )
        raised.append((warning, gives))
    paths = [path for _, path, _ in kept] + [Path(file.name) for file in files]
    runs = [
        {
            "file": str(paths[place]) if place < len(paths) else None,
            "kept": place < len(kept),
            "category": overall(judge(frame, list(records))).category if records else None,
        }
        for place, records in enumerate(asked.runs)
    ]
    if args.json:  # one document: what until_firm returns, and the warnings within it
        payload = {
            **_which(frame),
            "runs": runs,
            "made": len(made),
            "usage": asked.usage,
            "unthought": asked.unthought,
            "firm": asked.firm,
            "category": asked.category,
            "shares": asked.shares,
            "findings": [finding.as_dict() for finding in asked.findings],
            "stopped": asked.stopped,
            "openings": dict(openings.most_common()),
            "exit": status,
            "warnings": [described(warning, gives) for warning, gives in raised],
        }
        print(json.dumps(payload, indent=2))
        return status
    print(f"frame: {plain(frame.name)} ({frame.hash})")
    for place, read in enumerate(runs, 1):
        how = "kept" if read["kept"] else "asked now"
        print(f"run {place}: {plain(read['category'] or 'no category')}, {how}")
    many = len(asked.runs)
    state = f"{'yes' if asked.firm else 'no'}, {plain(asked.category or 'no category')}"
    state += f" after {many} run{'s' * (many != 1)}"
    shares = asked.shares
    if len(shares) == 1:
        state += f", read alike in {_percent(next(iter(shares.values())))} of draws"
    elif shares:
        alike = ", ".join(f"{plain(x)} {_percent(share)}" for x, share in shares.items())
        state += f", read alike in {alike} of draws"
    if not asked.firm and not asked.stopped and many >= most:
        state += ", as many runs as --most reads"
    print(f"firm: {state}; {len(made)} calls made now{_tokens(asked.usage, asked.unthought)}")
    for warning, _ in raised:
        notes = list(getattr(warning, "__notes__", []))
        print(f"{type(warning).__name__}: {warning}", *notes, sep="\n", file=sys.stderr)
    return status


def _tokens(usage: dict[str, int], reasoned: dict[str, Any] | None = None) -> str:
    # the tokens the calls made now reported, in and out, and the reasoning
    # among those out, then how many calls reported none; nothing for a count
    # no call reported
    said = []
    if "input_tokens" in usage:
        said.append(f"{usage['input_tokens']:,} tokens in")
    if "output_tokens" in usage:
        said.append(f"{usage['output_tokens']:,} out")
        if "reasoning_tokens" in usage:
            said.append(f"{usage['reasoning_tokens']:,} of them reasoning")
    elif "reasoning_tokens" in usage:  # a battery may report reasoning alone
        said.append(f"{usage['reasoning_tokens']:,} reasoning tokens")
    if reasoned and reasoned["calls"]:
        said.append(f"{reasoned['unthought']} of {reasoned['calls']} calls unthought")
    return "".join(f", {part}" for part in said)


def command_gate(args) -> int:
    """`gadfly gate`: what a fit did (`midwife.recoil.gate`), without a call.
    A successor that asks another question is a reframing, read against no
    category; any other is read from the runs --runs keeps, as `until_firm`
    reads them."""
    before, after = load_frame(args.before), load_frame(args.after)
    _bounds(args)
    most = recoil.most_of(after, args.most)  # one rule for every command, a reframing too
    asked = None
    if not recoil.reframes(before, after):
        if args.runs is None:
            raise UsageError(
                "a successor that asks the same question is read from its own runs",
                "name the folder that keeps them with --runs; gadfly firm makes them",
            )
        missing = "name the folder gadfly firm kept the successor's runs in"
        folder = _runs_folder(args.runs, missing, write=False)
        kept = _kept_runs(folder, after, most)
        if not kept:
            raise UsageError(
                f"folder {str(folder)!r} keeps no run of the successor",
                "gadfly firm asks it, and keeps each run there",
            )
        runs = [records for _, _, records in kept]
        asked = recoil.until_firm(
            after, None, Budget(calls=1), kept=runs, firm=args.firm, most=most
        )
    opened = recoil.gate(before, after, asked)
    if args.json:
        document = {
            **_which(after),
            "of": _which(before),
            "gate": opened.gate,
            "category": opened.category,
            "climbs": [_piece_document(piece) for piece in opened.climbs],
            "changed": list(opened.changed),
            "open": opened.open,
            "runs": 0 if asked is None else len(asked.runs),
            "firm": None if asked is None else asked.firm,
            "shares": None if asked is None else asked.shares,
        }
        print(json.dumps(document, indent=2))
        return 0
    print(f"successor: {_short(after)}, of {_short(before)}")
    if asked is not None:
        print(f"runs: {len(asked.runs)} read, {'firm' if asked.firm else 'not firm'}")
    print(f"gate: {opened.gate}")
    if opened.category:
        print(f"category: {opened.category}")
    for piece in opened.climbs:
        print(f"climbs: {piece.text!r}, of kind {plain(piece.kind)}")
    if opened.changed:
        print(f"changed: {', '.join(opened.changed)}")
    if opened.open:
        print(f"open: {opened.open}")
    return 0


def parser() -> argparse.ArgumentParser:
    """The command line's arguments."""
    root = Parser(
        prog="gadfly",
        description="Test whether a decision rests on the evidence you think it does.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,  # a shortened flag would change meaning when one is added
    )
    root.add_argument("--version", action="version", version=f"gadfly {__version__}")
    commands = root.add_subparsers(dest="command", metavar="command")
    command = functools.partial(commands.add_parser, allow_abbrev=False)

    show = command("plan", help="show trials and call count without spending")
    show.add_argument("frame", help="the frame, a JSON file, or - for stdin")
    show.add_argument(
        "--agreement",
        type=float,
        help="how often the reader gives its usual answer, from 0 to 1: shows the quorum's power",
    )
    show.add_argument(
        "--most",
        type=int,
        help=f"count the calls asking until firm makes over at most this many runs "
        f"(the frame's standing.most, else {recoil.MOST}, with --runs)",
    )
    show.add_argument(
        "--runs", metavar="FOLDER", help="the frame's runs gadfly firm keeps, counted as made"
    )
    show.add_argument("--json", action="store_true", help="print JSON instead of text")
    show.set_defaults(func=command_plan)

    execute = command("run", help="run a battery and keep records as JSON Lines")
    execute.add_argument("frame", help="the frame, a JSON file, or - for stdin")
    execute.add_argument("--battery", required=True, help="module:Class")
    execute.add_argument(
        "--out", "-o", "--output", required=True, help="a new JSON Lines file, or - for stdout"
    )
    execute.add_argument(
        "--calls", required=True, type=_calls, help="the most calls to make, or auto for a run's"
    )
    execute.add_argument("--output-tokens", type=int, default=64, help="each answer's cap")
    execute.add_argument("--token-budget", type=int, help="the most output tokens in all")
    execute.add_argument("--only", action="append", help="a trial id; may repeat")
    execute.add_argument("--kept", help="records already made: their calls are not made again")
    execute.add_argument(
        "--settle", action="store_true", help="stop a trial once its level cannot change"
    )
    execute.add_argument(
        "--stop-unresolved",
        action="store_true",
        help="ask the decisive trials first; stop an input once nothing can resolve it",
    )
    execute.add_argument(
        "--parallel", type=int, default=1, help="calls at once, for a battery that takes them"
    )
    execute.add_argument(
        "--withhold",
        metavar="FILE",
        help="refuse before any call a frame holding text it withholds",
    )
    execute.add_argument("--json", action="store_true", help="print JSON instead of text")
    execute.set_defaults(func=command_run)

    report = command("report", help="judge a kept JSON Lines file")
    report.add_argument("frame", help="the frame the records were made under, or - for stdin")
    report.add_argument("records", help="the records, a JSON Lines file, or - for stdin")
    report.add_argument("--json", action="store_true", help="print JSON instead of text")
    report.set_defaults(func=command_report)

    check = command("check-frame", help="check a frame before any call")
    check.add_argument("frame", help="the frame, a JSON file, or - for stdin")
    check.add_argument(
        "--withhold", metavar="FILE", help="also refuse a frame holding text it withholds"
    )
    check.add_argument("--json", action="store_true", help="print JSON instead of text")
    check.set_defaults(func=command_check_frame)

    portfolio = command("portfolio", help="count verdicts across report files")
    portfolio.add_argument(
        "reports", nargs="+", help="documents from `gadfly report --json`, one may be -"
    )
    portfolio.add_argument("--json", action="store_true", help="print JSON instead of text")
    portfolio.set_defaults(func=command_portfolio)
    counted = command("stats", help="how firm each trial and verdict is over kept runs")
    counted.add_argument("frame", help="the frame the records were made under, or - for stdin")
    counted.add_argument("records", nargs="+", help="kept runs, JSON Lines files, one may be -")
    counted.add_argument(
        "--pool",
        nargs=2,
        action="append",
        metavar=("FRAME", "RECORDS"),
        help="calls another frame made with the same reader and prompt; may repeat",
    )
    counted.add_argument(
        "--resamples",
        type=int,
        default=stats.RESAMPLES,
        help="draws of each run for its verdict's stability; 0 leaves them out",
    )
    counted.add_argument("--json", action="store_true", help="print JSON instead of text")
    counted.set_defaults(func=command_stats)

    # recoil's steps, each `midwife.recoil`'s function of the same name
    def piece(sub: argparse.ArgumentParser, text: bool = False) -> None:
        # the piece, as walk and successor take it: found in a frame, or for
        # successor a text of its own, as Python's Piece(text, kind) is
        sub.add_argument(
            "--from",
            dest="source",
            required=not text,
            metavar="FRAME",
            help="the frame the piece was found in, a JSON file, or - for stdin",
        )
        which = sub.add_mutually_exclusive_group(required=True)
        which.add_argument("--span", help="the piece is this span of that frame")
        which.add_argument(
            "--decision", metavar="LABEL", help="the piece is that frame's decision, read as LABEL"
        )
        if text:
            which.add_argument(
                "--text", help="the piece is this text, found in no frame; with --kind"
            )
            sub.add_argument("--kind", help="the kind of hole the --text piece fills")

    def reading(
        sub: argparse.ArgumentParser,
    ) -> None:  # how runs are read, as until_firm reads them
        sub.add_argument(
            "--firm",
            type=float,
            default=recoil.FIRM,
            help=f"the share of draws that must read each input alike (default {recoil.FIRM})",
        )
        sub.add_argument(
            "--most",
            type=int,
            help=f"the most runs read, kept ones included (the frame's own, else {recoil.MOST})",
        )

    walked = command("walk", help="where a piece climbs through frames, without spending")
    walked.add_argument("frames", nargs="+", help="the frames to climb, JSON files, one may be -")
    piece(walked)
    walked.add_argument(
        "--made",
        action="append",
        metavar="RECORDS",
        help="a crossing's run, JSON Lines: a frame quoting an artefact it made climbs to it; "
        "may repeat",
    )
    walked.add_argument(
        "--sideways",
        action="store_true",
        help="offer the piece one step aside too, to each frame quoting a text --from quotes",
    )
    walked.add_argument(
        "--vectors",
        metavar="FILE",
        help="order the fits by cosine, from these whole-text vectors, JSON Lines, or - for stdin",
    )
    walked.add_argument(
        "--space", metavar="ID", help="the space to order by, when --vectors holds several"
    )
    walked.add_argument(
        "--calls", type=int, help="the calls to ask fits with, each until firm, in order"
    )
    walked.add_argument(
        "--most",
        type=int,
        help=f"the most runs each fit may take, with --calls (default {recoil.MOST})",
    )
    walked.add_argument("--json", action="store_true", help="print JSON instead of text")
    walked.set_defaults(func=command_walk)

    drafted = command("successor", help="draft the frame a fit is asked again as")
    drafted.add_argument("frame", help="the frame the piece fits, a JSON file, or - for stdin")
    drafted.add_argument("--hole", required=True, help="the hole the piece fills")
    piece(drafted, text=True)
    drafted.add_argument(
        "--after",
        metavar="SPAN",
        help="place the piece right after this span, the line it amends (default: last)",
    )
    drafted.add_argument(
        "--set",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        help="set a key of the successor to a JSON value; may repeat",
    )
    drafted.add_argument(
        "--out", "-o", "--output", default="-", help="a new JSON file, or - for stdout (default)"
    )
    drafted.add_argument("--json", action="store_true", help="print JSON instead of text")
    drafted.set_defaults(func=command_successor)

    firmed = command("firm", help="ask a frame run by run until its verdict is firm")
    firmed.add_argument("frame", help="the frame, a JSON file, or - for stdin")
    firmed.add_argument("--battery", required=True, help="module:Class")
    firmed.add_argument(
        "--runs",
        required=True,
        metavar="FOLDER",
        help="the frame's runs, 1.jsonl and on: kept ones are read, new ones added",
    )
    firmed.add_argument(
        "--calls",
        required=True,
        type=_calls,
        help="the most calls to make, or auto for the most --most runs can take",
    )
    firmed.add_argument("--output-tokens", type=int, default=64, help="each answer's cap")
    firmed.add_argument("--token-budget", type=int, help="the most output tokens in all")
    firmed.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="calls at once within each run, for a battery that takes them",
    )
    firmed.add_argument(
        "--withhold",
        metavar="FILE",
        help="refuse before any call a frame holding text it withholds",
    )
    reading(firmed)
    firmed.add_argument("--json", action="store_true", help="print JSON instead of text")
    firmed.set_defaults(func=command_firm)

    gated = command("gate", help="read what a fit did, without spending")
    gated.add_argument("before", help="the frame the piece fits, a JSON file, or - for stdin")
    gated.add_argument("after", help="its successor, a JSON file, or - for stdin")
    gated.add_argument(
        "--runs", metavar="FOLDER", help="the successor's runs, as gadfly firm keeps them"
    )
    reading(gated)
    gated.add_argument("--json", action="store_true", help="print JSON instead of text")
    gated.set_defaults(func=command_gate)

    root.commands = {"plan": show, "run": execute, "report": report, "check-frame": check}
    root.commands.update(portfolio=portfolio, stats=counted)
    root.commands.update(walk=walked, successor=drafted, firm=firmed, gate=gated)
    return root


TROUBLESHOOTING = "https://mirzahusadzic.github.io/gadfly/troubleshooting"


def _utf8() -> None:
    """Standard output and error carry UTF-8 on every platform, as Gadfly's
    files do. Before Python 3.15 a Windows pipe takes the code page, which
    lacks most of Unicode, and a ✓ in a frame would end the command."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8", errors=stream.errors)


def main(argv: list[str] | None = None) -> int:
    """Run one command. A refusal prints its class and message, then its
    notes, and exits with its class's status; with `--json`, the same as one
    object on standard error. Anything else is a bug: its traceback, and 70."""
    program = argv is None
    if program:
        _utf8()
    if program and hasattr(signal, "SIGPIPE"):
        # run as the program: a reader that stops reading (`| head`) ends it at
        # once and quietly, as it ends any Unix tool (status 141 in a shell)
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    argv = sys.argv[1:] if argv is None else argv
    command_line = parser()
    # until the arguments are read, --json is asked for only among the options
    as_json = "--json" in (argv[: argv.index("--")] if "--" in argv else argv)
    try:
        args = command_line.parse_args(argv)
        as_json = bool(getattr(args, "json", False))
        if args.command is None:  # no command: what the tool does, not an error
            command_line.print_help()
            return 0
        named = [vars(args).get(key) for key in ("frame", "records", "kept", "source", "vectors")]
        named.append(vars(args).get("withhold"))
        named += [vars(args).get(key) for key in ("before", "after")]  # gate's two frames
        # stats takes several records, portfolio reports, walk frames and made runs
        for many in ("records", "reports", "frames", "made"):
            if isinstance(vars(args).get(many), list):
                named += vars(args)[many]
        named += [path for pair in vars(args).get("pool") or [] for path in pair]
        if named.count("-") > 1:
            raise UsageError("standard input is read once", "name - for one file at most")
        try:
            return args.func(args)
        except SystemExit:  # no command of Gadfly's exits so: a battery's sys.exit, a bug
            traceback.print_exc()
            return errors.BUG
    except BrokenPipeError as error:  # no SIGPIPE ended it (Windows): end as it would
        if program:  # what is left unwritten, the flush at exit too, goes nowhere
            with contextlib.suppress(OSError, ValueError):
                os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        if getattr(error, "running", 0):  # a call hung in its thread would hold the exit
            os._exit(errors.PIPE)
        return errors.PIPE
    except (GadflyError, OSError, KeyboardInterrupt) as error:
        status = refused(error, as_json)
        if getattr(error, "running", 0):  # a call hung in its thread would hold the exit
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(status)
        return status
    except Exception:
        traceback.print_exc()
        return errors.BUG  # Gadfly's fault, not the caller's


def refused(error: BaseException, as_json: bool) -> int:
    """Say a refusal as the last lines of a Python traceback, or as JSON, and
    give its exit status: a GadflyError's own, 7 for a file, 130 for Ctrl-C."""
    if isinstance(error, GadflyError):
        status, anchor, message = error.exit, type(error).__name__.lower(), str(error)
    elif isinstance(error, OSError):
        status, anchor, message = errors.FILE, "file-errors", _plain(error)
    else:
        status, anchor = errors.INTERRUPTED, "keyboardinterrupt"
        message = str(error) or "stopped by Ctrl-C"
    if as_json:
        print(
            json.dumps({"error": described(error, status, message, anchor)}, indent=2),
            file=sys.stderr,
        )
    else:
        notes = list(getattr(error, "__notes__", []))
        print(f"{type(error).__name__}: {message}", *notes, sep="\n", file=sys.stderr)
    return status


def described(problem: BaseException, status: int, message: str = "", anchor: str = "") -> dict:
    """A refusal or a warning as JSON: its type, the exit status it gives, its
    message and notes, and its troubleshooting section."""
    kind = type(problem).__name__
    return {
        "type": kind,
        "exit": status,
        "message": message or str(problem),
        "notes": list(getattr(problem, "__notes__", [])),
        "help": f"{TROUBLESHOOTING}#{anchor or kind.lower()}",
    }


def _plain(error: OSError) -> str:
    # Python's own words carry an errno and a colon; ours are plain already
    if error.filename is None:
        return str(error)
    name = str(error.filename)
    return {
        errno.ENOENT: f"file {name!r} does not exist",
        errno.EACCES: f"file {name!r} cannot be read or written here",
        errno.EISDIR: f"{name!r} is a folder, not a file",
        errno.ENOTDIR: f"path {name!r} runs through a file, not a folder",
    }.get(error.errno, f"file {name!r} cannot be used ({error.strerror})")


# a value argparse quotes, as Python's repr does, with either quote
QUOTED = re.compile(r"""('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")""")
# a value that starts with a hyphen and is a number, never a flag
NUMBER = re.compile(r"-(?:\d+(?:\.\d*)?|\.\d+)")


class Parser(argparse.ArgumentParser):
    """The arguments; a mistake in them is a UsageError."""

    commands: dict[str, Parser] = {}

    def parse_args(self, args=None, namespace=None):
        """The arguments; one no command takes is that command's mistake,
        said before any that is missing, since a mistyped flag is often what
        is missing."""
        args = sys.argv[1:] if args is None else list(args)
        unknown = self.unknown(args)
        if unknown:
            command = next((token for token in args if token in self.commands), None)
            parser = self.commands.get(command, self)
            parser.error(f"unrecognized arguments {' '.join(map(plain, unknown))}")
        parsed, extra = self.parse_known_args(args, namespace)
        if extra:  # the command's own mistake, pointing at its own help
            parser = self.commands.get(getattr(parsed, "command", None), self)
            parser.error(f"unrecognized arguments {' '.join(map(plain, extra))}")
        return parsed

    def unknown(self, args: list[str]) -> list[str]:
        """The flags in `args` that neither Gadfly nor the command takes."""
        tokens = args[: args.index("--")] if "--" in args else args
        known = set(self._option_string_actions)
        command = next((token for token in tokens if token in self.commands), None)
        if command:
            known |= set(self.commands[command]._option_string_actions)
        return [
            token
            for token in tokens
            if token.startswith("-")
            and token != "-"
            and not NUMBER.fullmatch(token)
            and token.split("=", 1)[0] not in known
        ]

    def error(self, message: str):
        """Refuse as a UsageError, in one clause, pointing at the help."""
        required = re.fullmatch(r"the following arguments are required: (.+)", message)
        clash = re.fullmatch(r"argument (\S+): not allowed with argument (\S+)", message)
        choice = re.fullmatch(r"one of the arguments (.+) is required", message)
        if required:
            message = f"missing {required[1]}"
        elif clash:  # two flags of one group, as walk's --span and --decision,
            # named in one order whichever was typed first
            first, second = sorted((clash[1], clash[2]))
            message = f"{first} and {second} cannot be given together"
        elif choice:  # one flag of a group, as walk's piece is a --span or a --decision
            message = f"missing one of {', '.join(choice[1].split())}"
        else:  # argparse's words hold colons: "argument --calls: invalid int value: 'x'"
            message = re.sub(r"^argument (\S+): ", r"\1, ", message)
        # the colons argparse adds go, a value's own stay inside its quotes
        parts = QUOTED.split(message)
        parts[::2] = [part.replace(": ", " ") for part in parts[::2]]
        raise UsageError("".join(parts), f"{self.prog} --help shows its arguments")


if __name__ == "__main__":
    raise SystemExit(main())
