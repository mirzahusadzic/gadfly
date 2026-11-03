"""The command line: plan, run, report, check-frame, portfolio.

    uv run gadfly plan examples/upgrade.json
    uv run gadfly run examples/upgrade.json \\
        --battery midwife.batteries.egemma:EGemma \\
        --calls 40 --out records.jsonl
    uv run gadfly report examples/upgrade.json records.jsonl
    uv run gadfly check-frame my-frame.json
    uv run gadfly portfolio a.json b.json

It uses only the public pipeline. `run` needs an explicit call budget,
writes each record as one JSON line the moment it exists, never writes over
a file and makes none when it is refused, and says when it stopped early;
`report` keeps a finding's evidence and its open obligations apart.
A battery is named `module:Class` and is imported from the current
directory.
"""

from __future__ import annotations

import argparse
import errno
import functools
import importlib
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

from . import __version__, errors, stats
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
from .pipeline import calls_needed, judge, overall, plan, run, situate
from .portfolio import entry_from, summarize
from .types import Battery, Budget, Record
from .verdict import settled, unreachable

EXAMPLES = """\
examples:
  gadfly check-frame my-frame.json      check a frame, with no call
  gadfly plan my-frame.json             its trials and their cost, with no call
  gadfly run my-frame.json --battery midwife.batteries.egemma:EGemma \\
      --calls 40 --out records.jsonl    make the calls, keeping each record
  gadfly report my-frame.json records.jsonl
                                        read the verdict, with no call

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
        f"frame: {frame.name} ({frame.hash})",
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
    without a call."""
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
    if args.json:
        print(json.dumps(body, indent=2))
    else:
        print(f"{body['frame']} ({body['hash']}): {body['calls']} calls")
        if power is not None:
            print(f"power: {_powered(power)}")
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


def _powered(power: stats.Power) -> str:
    # one line: what the quorum can resolve at the reader's agreement
    return (
        f"at {_percent(power.agreement)} agreement, a trial reaches a level of "
        f"{power.agree} of {power.quorum} {_percent(power.trial)} of the time, and all "
        f"{power.trials} trials an input needs {_percent(power.input)}"
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
    for x, rows in compared.items():
        print(f"input {plain(x)}")
        for row in rows:
            answers = ", ".join(f"{plain(label)} {n}" for label, n in row.answers.items())
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
            again = ", ".join(f"{c} {_percent(s)}" for c, s in drawn.get(x, {}).items())
            print(
                f"  run {place}, {plain(x)}  {category}"
                + (f"; drawn again {again}" if again else "")
            )
    return 0


def command_run(args) -> int:
    """`gadfly run`: every planned call the budget covers, each record kept."""
    frame = load_frame(args.frame)
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
    # a new file: never another run's, nor what a link, even a broken one, points at
    if not streamed and out.is_dir() and not out.is_symlink():
        raise noted(
            IsADirectoryError(f"{str(out)!r} is a folder, not a file"),
            "name a new file in it, or choose another --out",
        )
    if not streamed and os.path.lexists(out):
        raise noted(
            FileExistsError(f"file {str(out)!r} exists already"),
            "kept records are never written over; choose a new --out, or finish it with --kept",
        )
    if not streamed and out.parent.exists() and not out.parent.is_dir():
        raise noted(
            NotADirectoryError(f"path {str(out)!r} runs through a file, not a folder"),
            "choose another --out",
        )
    if not streamed and not out.parent.is_dir():  # found out before a call is spent
        raise noted(
            FileNotFoundError(f"folder {str(out.parent)!r} does not exist"),
            "make it, or choose another --out",
        )
    if not streamed and not os.access(out.parent, os.W_OK):
        raise noted(
            PermissionError(f"folder {str(out.parent)!r} cannot be written"),
            "choose another --out",
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


def command_report(args) -> int:
    """`gadfly report`: the verdict read from a kept JSON Lines file."""
    frame = load_frame(args.frame)
    records = load_records(args.records)
    if args.json:
        findings = judge(frame, records)
        document = {
            "frame": frame.name,
            "hash": frame.hash,
            "overall": overall(findings).as_dict(),
            "findings": [finding.as_dict() for finding in findings],
        }
        print(json.dumps(document, indent=2))
    else:
        print(render_report(frame, records))
    return 0


def command_check_frame(args) -> int:
    """`gadfly check-frame`: the frame's shape against the schema (when
    jsonschema is installed), then the parser's authoritative refusal."""
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
    if problems and args.json:  # one FrameError, as every refusal is, listing them all
        said = {"type": "FrameError", "exit": FrameError.exit, "message": problems[0]["problem"]}
        said |= {"notes": problems[0]["notes"], "help": f"{TROUBLESHOOTING}#frameerror"}
        said |= {"checked": checked, "problems": problems}
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
        print(json.dumps(result, indent=2))
    else:
        print(f"ok ({checked}): {frame.name} ({frame.hash}), {calls_needed(frame)} calls")
    return FrameError.exit if problems else 0


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
    show.add_argument("--json", action="store_true", help="print JSON instead of text")
    show.set_defaults(func=command_plan)

    execute = command("run", help="run a battery and keep records as JSON Lines")
    execute.add_argument("frame", help="the frame, a JSON file, or - for stdin")
    execute.add_argument("--battery", required=True, help="module:Class")
    execute.add_argument(
        "--out", "-o", "--output", required=True, help="a new JSON Lines file, or - for stdout"
    )
    execute.add_argument("--calls", required=True, type=int, help="the most calls to make")
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
    execute.add_argument("--json", action="store_true", help="print JSON instead of text")
    execute.set_defaults(func=command_run)

    report = command("report", help="judge a kept JSON Lines file")
    report.add_argument("frame", help="the frame the records were made under, or - for stdin")
    report.add_argument("records", help="the records, a JSON Lines file, or - for stdin")
    report.add_argument("--json", action="store_true", help="print JSON instead of text")
    report.set_defaults(func=command_report)

    check = command("check-frame", help="check a frame before any call")
    check.add_argument("frame", help="the frame, a JSON file, or - for stdin")
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
    root.commands = {"plan": show, "run": execute, "report": report, "check-frame": check}
    root.commands.update(portfolio=portfolio, stats=counted)
    return root


TROUBLESHOOTING = "https://mirzahusadzic.github.io/gadfly/troubleshooting"


def main(argv: list[str] | None = None) -> int:
    """Run one command. A refusal prints its class and message, then its
    notes, and exits with its class's status; with `--json`, the same as one
    object on standard error. Anything else is a bug: its traceback, and 70."""
    if argv is None and hasattr(signal, "SIGPIPE"):
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
        named = [vars(args).get(key) for key in ("frame", "records", "kept")]
        if [*named, *vars(args).get("reports", [])].count("-") > 1:
            raise UsageError("standard input is read once", "name - for one file at most")
        try:
            return args.func(args)
        except SystemExit:  # no command of Gadfly's exits so: a battery's sys.exit, a bug
            traceback.print_exc()
            return errors.BUG
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


class Parser(argparse.ArgumentParser):
    """The arguments; a mistake in them is a UsageError."""

    commands: dict[str, Parser] = {}

    def parse_args(self, args=None, namespace=None):
        """The arguments; one no command takes is that command's mistake."""
        parsed, extra = self.parse_known_args(args, namespace)
        if extra:  # the command's own mistake, pointing at its own help
            parser = self.commands.get(getattr(parsed, "command", None), self)
            parser.error(f"unrecognized arguments {' '.join(map(plain, extra))}")
        return parsed

    def error(self, message: str):
        """Refuse as a UsageError, in one clause, pointing at the help."""
        # argparse's words hold colons: "argument --calls: invalid int value: 'x'"
        message = re.sub(r"^argument (\S+): ", r"\1, ", message)
        message = message.replace("the following arguments are required: ", "missing ")
        # the colons argparse adds go, a value's own stay inside its quotes
        parts = QUOTED.split(message)
        parts[::2] = [part.replace(": ", " ") for part in parts[::2]]
        raise UsageError("".join(parts), f"{self.prog} --help shows its arguments")


if __name__ == "__main__":
    raise SystemExit(main())
