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
a file and makes none until its first record, and says when it stopped
early; `report` keeps a finding's evidence and its open obligations apart.
A battery is named `module:Class` and is imported from the current
directory.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .frame import FrameError, schema
from .pipeline import calls_needed, judge, overall, plan, run, situate
from .portfolio import entry_from, summarize
from .types import Budget, Record


def load_frame(path: str):
    """The frame in a JSON file, checked and hashed."""
    return situate(json.loads(Path(path).read_text(encoding="utf-8")))


def load_battery(spec: str):
    """An instance of the battery class `module:Class`."""
    module_name, sep, attribute = spec.partition(":")
    if not sep or not module_name or not attribute:
        raise ValueError("--battery is module:Class (for example midwife.batteries.egemma:EGemma)")
    if os.getcwd() not in sys.path:  # as `python -m` would: your module, from here
        sys.path.insert(0, os.getcwd())
    target = getattr(importlib.import_module(module_name), attribute)
    return target() if isinstance(target, type) else target


def load_records(path: str) -> list[dict[str, Any]]:
    """The records kept in a JSON Lines file."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def render_report(frame, records: list[dict[str, Any]]) -> str:
    """The person-readable report: the overall category, then each input's
    levels, evidence and open obligations, each on its own line."""
    findings = judge(frame, records)
    combined = overall(findings)
    rows = [
        f"frame: {frame.name} ({frame.hash})",
        f"records: {len(records)}  planned calls: {calls_needed(frame)}",
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


def command_plan(args) -> int:
    """`gadfly plan`: the trials and the call count, without a call."""
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
                "body": trial.body_hash,
            }
            for trial in trials
        ],
    }
    if args.json:
        print(json.dumps(body, indent=2))
    else:
        print(f"{body['frame']} ({body['hash']}): {body['calls']} calls")
        for trial in trials:
            print(f"  {trial.id:12} {trial.kind:12} body {trial.body_hash[:12]}")
    return 0


def command_run(args) -> int:
    """`gadfly run`: every planned call the budget covers, each record kept."""
    frame = load_frame(args.frame)
    battery = load_battery(args.battery)
    kept = load_records(args.kept) if args.kept else []
    out = Path(args.out)
    if out.exists():  # a new file: never another run's
        raise FileExistsError(f"{out} exists: kept records are never written over")
    files = []  # the file is made by the first record, so a refused run leaves none

    def keep(record: Record) -> None:
        if not files:
            files.append(out.open("x", encoding="utf-8"))
            for old in kept:  # the kept records first, so the new file is the whole run
                files[0].write(json.dumps(old, ensure_ascii=False) + "\n")
        files[0].write(json.dumps(record.as_dict(), ensure_ascii=False) + "\n")
        files[0].flush()

    try:
        result = run(
            frame,
            battery,
            Budget(args.calls, args.output_tokens, args.token_budget),
            on_record=keep,
            only=args.only,
            kept=kept,
        )
    finally:
        for file in files:
            file.close()
    # a service that is down answers every call with an opening: say so, so a
    # run that spent its calls on nothing does not read as a finished one
    openings = Counter(r.opening for r in result.records if r.opening is not None)
    if args.json:
        payload = {
            "frame": frame.name,
            "hash": frame.hash,
            "out": str(out),
            "planned": result.planned,
            "made": len(result.records),
            "kept": len(kept) if files else 0,
            "stopped": result.stopped,
            "openings": dict(openings.most_common()),
        }
        print(json.dumps(payload, indent=2))
    else:
        before = (
            f", after {len(kept)} kept record{'s' * (len(kept) != 1)}" if kept and files else ""
        )
        print(f"wrote {len(result.records)}/{result.planned} calls to {out}{before}")
        if openings:
            reason, count = openings.most_common(1)[0]
            total = sum(openings.values())
            print(
                f'openings: {total} of {len(result.records)} calls, most often "{reason}" ({count})'
            )
        if result.stopped:
            print(f"stopped: {result.stopped}")
    return 0


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
    raw = json.loads(Path(args.frame).read_text(encoding="utf-8"))
    problems = []
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        checked = "parser"
    else:
        checked = "schema and parser"
        for error in sorted(Draft202012Validator(schema()).iter_errors(raw), key=str):
            where = "/" + "/".join(str(part) for part in error.absolute_path)
            problems.append({"at": where, "problem": error.message})
    try:
        frame = situate(raw)
    except FrameError as error:
        frame, problems = None, [*problems, {"at": "/", "problem": str(error)}]
    if args.json:
        result = {"ok": not problems, "checked": checked, "problems": problems}
        if frame and not problems:
            result.update(frame=frame.name, hash=frame.hash, calls=calls_needed(frame))
        print(json.dumps(result, indent=2))
    elif problems:
        for problem in problems:
            print(f"{problem['at']}: {problem['problem']}")
    else:
        print(f"ok ({checked}): {frame.name} ({frame.hash}), {calls_needed(frame)} calls")
    return 1 if problems else 0


def command_portfolio(args) -> int:
    """`gadfly portfolio`: several reports counted side by side."""
    documents = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.reports]
    print(json.dumps(summarize([entry_from(document) for document in documents]), indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    """The command line's arguments."""
    root = argparse.ArgumentParser(prog="gadfly", description=__doc__.split("\n\n")[0])
    commands = root.add_subparsers(dest="command", required=True)

    show = commands.add_parser("plan", help="show trials and call count without spending")
    show.add_argument("frame")
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=command_plan)

    execute = commands.add_parser("run", help="run a battery and keep records as JSON Lines")
    execute.add_argument("frame")
    execute.add_argument("--battery", required=True, help="module:Class")
    execute.add_argument("--out", required=True, help="a new JSON Lines file")
    execute.add_argument("--calls", required=True, type=int, help="the most calls to make")
    execute.add_argument("--output-tokens", type=int, default=64, help="each answer's cap")
    execute.add_argument("--token-budget", type=int, help="the most output tokens in all")
    execute.add_argument("--only", action="append", help="a trial id; may repeat")
    execute.add_argument("--kept", help="records already made: their calls are not made again")
    execute.add_argument("--json", action="store_true")
    execute.set_defaults(func=command_run)

    report = commands.add_parser("report", help="judge a kept JSON Lines file")
    report.add_argument("frame")
    report.add_argument("records")
    report.add_argument("--json", action="store_true")
    report.set_defaults(func=command_report)

    check = commands.add_parser("check-frame", help="check a frame before any call")
    check.add_argument("frame")
    check.add_argument("--json", action="store_true")
    check.set_defaults(func=command_check_frame)

    portfolio = commands.add_parser("portfolio", help="count verdicts across report files")
    portfolio.add_argument("reports", nargs="+", help="documents from `gadfly report --json`")
    portfolio.set_defaults(func=command_portfolio)
    return root


def main(argv: list[str] | None = None) -> int:
    """Run one command; a refusal is a message and exit status 2."""
    args = parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, RuntimeError, KeyError, ImportError) as error:
        print(f"gadfly: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
