"""The command line's less trodden paths, as a person or a script meets
them: a run counted at a terminal or stopped by Ctrl-C with a call still
out, a battery that refuses to be made, a frame checked without jsonschema
or too deep for it, a portfolio's shared obligations, firm's quieter
warnings, and the command run as the program itself."""

import errno
import io
import json
import os
import runpy
import signal
import sys
from pathlib import Path

import pytest

from midwife.cli import main

ROOT = Path(__file__).parent.parent
REFUND = str(ROOT / "tests/fixtures/refund.json")
RULES = ["--battery", "tests.fixtures.refund:RuleReader", "--calls", "8"]


@pytest.fixture(autouse=True)
def at_root(monkeypatch):
    monkeypatch.chdir(ROOT)  # the battery is imported from here


class Terminal(io.StringIO):
    """A terminal: standard input with nothing piped in, or standard error
    a person reads."""

    def isatty(self):
        return True


class Pressed(Terminal):
    """A person at the terminal who presses Ctrl-C twice once the first call
    is counted: the first press lets the calls out end, the second waits for
    none of them."""

    pressed = False

    def write(self, text):
        written = super().write(text)
        if text.endswith("\r1 calls made") and not self.pressed:
            self.pressed = True
            for _ in range(2):  # raised, not sent: Windows's os.kill would end the tests
                signal.raise_signal(signal.SIGINT)
        return written


def own_battery(tmp_path, monkeypatch, name, source):
    # a battery module of the caller's own, importable from here for this test
    monkeypatch.syspath_prepend(str(tmp_path))
    (tmp_path / f"{name}.py").write_text(source, encoding="utf-8")


# ---- run


def test_run_counts_its_calls_in_a_terminal(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("sys.stderr.isatty", lambda: True)
    assert main(["run", REFUND, *RULES, "--out", str(tmp_path / "records.jsonl")]) == 0
    err = capsys.readouterr().err
    assert err.startswith("\r1 calls made\r2 calls made") and err.endswith("\r8 calls made\n")
    assert main(["run", REFUND, *RULES, "--out", str(tmp_path / "again.jsonl"), "--json"]) == 0
    assert capsys.readouterr().err == ""  # a script reads the one document, no count


def test_ctrl_c_before_any_record_says_none_was_kept(tmp_path, capsys):
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:InterruptedAtOnce", "--calls", "8"]
    assert main([*argv, "--out", str(out)]) == 130
    assert capsys.readouterr().err.splitlines() == [
        "KeyboardInterrupt: stopped by Ctrl-C after 0 calls, and no record was kept"
    ]
    assert not out.exists()


def test_a_second_ctrl_c_with_a_call_hung_says_so_and_exits_past_it(tmp_path, monkeypatch):
    # in process, as the subprocess test cannot be measured: the person
    # presses twice once a call is counted, and the call still out is
    # neither waited for nor dropped in silence
    own_battery(
        tmp_path,
        monkeypatch,
        "hanging_battery",
        "import threading\n"
        "from tests.fixtures.refund import RuleReader\n"
        "release = threading.Event()\n"
        "class Reader(RuleReader):\n"
        "    concurrent = True\n"
        "    def __init__(self):\n"
        "        self.calls, self.lock = 0, threading.Lock()\n"
        "    def observe(self, frame, prompt, max_output_tokens):\n"
        "        with self.lock:\n"
        "            self.calls += 1\n"
        "            hangs = self.calls > 1\n"
        "        if hangs:\n"
        "            release.wait(10)\n"
        "        return super().observe(frame, prompt, max_output_tokens)\n",
    )
    exits, terminal = [], Pressed()
    monkeypatch.setattr(os, "_exit", exits.append)  # the exit past a hung thread, heard
    monkeypatch.setattr("sys.stderr", terminal)
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "hanging_battery:Reader", "--calls", "8"]
    before = signal.getsignal(signal.SIGINT)
    try:
        assert main([*argv, "--parallel", "2", "--out", str(out)]) == 130
    finally:
        made = sys.modules.pop("hanging_battery", None)
        if made is not None:
            made.release.set()  # the hung call ends with the test
    assert exits == [130] and signal.getsignal(signal.SIGINT) is before
    assert terminal.getvalue().split("\n") == [
        "\r1 calls made",
        f"KeyboardInterrupt: stopped by Ctrl-C after 1 calls; they are in file {str(out)!r}",
        f"finish with --kept {str(out)!r} and a new --out",
        "1 calls still out were left unanswered",
        "",
    ]
    assert len(out.read_text(encoding="utf-8").splitlines()) == 1


def test_run_shows_another_librarys_warning_as_python_would(tmp_path, capsys):
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:Warned", "--calls", "8"]
    with pytest.warns(UserWarning, match="^a library of the reader's warned$"):
        assert main([*argv, "--out", str(tmp_path / "records.jsonl")]) == 0
    told = capsys.readouterr()
    assert told.out.startswith("wrote 8/8 calls") and told.err == ""


def test_a_resume_with_nothing_left_prints_the_whole_run_to_standard_output(tmp_path, capsys):
    first = tmp_path / "records.jsonl"
    assert main(["run", REFUND, *RULES, "--out", str(first)]) == 0
    capsys.readouterr()
    assert main(["run", REFUND, *RULES, "--out", "-", "--kept", str(first)]) == 0
    told = capsys.readouterr()  # standard output is still open to read
    assert told.out == first.read_text(encoding="utf-8")
    assert told.err.splitlines()[0] == "wrote 0/0 calls to standard output, after 8 kept records"


# ---- batteries


def test_a_battery_of_your_own_that_refuses_to_be_made_is_quoted(tmp_path, capsys, monkeypatch):
    # Gadfly's own error class, raised by another's battery when it is made,
    # is that battery's words: quoted, never said as Gadfly's
    own_battery(
        tmp_path,
        monkeypatch,
        "unmade_battery",
        "from midwife.errors import BatteryError\n"
        "class Reader:\n"
        "    def __init__(self):\n"
        "        raise BatteryError('no key: set it')\n",
    )
    argv = ["run", REFUND, "--battery", "unmade_battery:Reader", "--calls", "8"]
    try:
        assert main([*argv, "--out", str(tmp_path / "r.jsonl")]) == 6
    finally:
        sys.modules.pop("unmade_battery", None)
    assert capsys.readouterr().err.splitlines() == [
        "BatteryError: battery 'unmade_battery:Reader' could not be made",
        "it said 'no key: set it'",
    ]
    assert not (tmp_path / "r.jsonl").exists()


def test_a_shipped_battery_that_refuses_to_be_made_says_so_in_gadflys_words(
    tmp_path, capsys, monkeypatch
):
    # eGemma's address is read from the environment when its module is
    # imported, as a fresh command imports it: one off this machine is refused
    import midwife.batteries
    import midwife.batteries.egemma

    monkeypatch.setenv("EGEMMA_URL", "http://example.com:8000")
    monkeypatch.setattr(midwife.batteries, "egemma", midwife.batteries.egemma)
    monkeypatch.delitem(sys.modules, "midwife.batteries.egemma")
    argv = ["run", REFUND, "--battery", "midwife.batteries.egemma:EGemma", "--calls", "8"]
    assert main([*argv, "--out", str(tmp_path / "r.jsonl")]) == 6
    assert capsys.readouterr().err.splitlines() == [
        "BatteryError: eGemma's address 'http://example.com:8000/judge' "
        "is not on this machine over http"
    ]
    assert not (tmp_path / "r.jsonl").exists()


# ---- check-frame, stats, portfolio, arguments


def test_check_frame_with_json_lists_no_withheld_places_unless_asked(capsys):
    assert main(["check-frame", REFUND, "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert (result["ok"], result["checked"], result["calls"]) == (True, "schema and parser", 8)
    assert "withheld" not in result


def test_check_frame_without_jsonschema_checks_with_the_parser_alone(capsys, monkeypatch):
    monkeypatch.setitem(sys.modules, "jsonschema", None)  # as where it is not installed
    assert main(["check-frame", REFUND]) == 0
    assert capsys.readouterr().out.startswith("ok (parser): refund-receipt (")


def test_check_frame_leaves_a_frame_too_deep_for_the_schema_to_the_parser(tmp_path, capsys):
    # JSON reads two lists 800 deep, but the schema's check of unique anchors
    # recurses past Python's limit: the parser's refusal is said alone
    deep = []
    for _ in range(800):
        deep = [deep]
    raw = json.loads(Path(REFUND).read_text(encoding="utf-8"))
    raw["anchors"] = [deep, deep]
    frame = tmp_path / "deep.json"
    frame.write_text(json.dumps(raw), encoding="utf-8")
    assert main(["check-frame", str(frame), "--json"]) == 4
    error = json.loads(capsys.readouterr().err)["error"]
    assert (error["type"], error["checked"]) == ("FrameError", "schema and parser")
    assert [problem["at"] for problem in error["problems"]] == ["/"]
    assert main(["check-frame", str(frame)]) == 4
    err = capsys.readouterr().err
    assert err.startswith(f"FrameError: {error['message']}\n") and "Traceback" not in err


def test_stats_of_pooled_calls_alone_measures_no_agreement(tmp_path, capsys):
    # no call of this frame's own: nothing was asked twice in a run of it
    raw = json.loads(Path(REFUND).read_text(encoding="utf-8"))
    again, made, none = tmp_path / "again.json", tmp_path / "again.jsonl", tmp_path / "none.jsonl"
    again.write_text(json.dumps({**raw, "name": "refund-again"}), encoding="utf-8")
    assert main(["run", str(again), *RULES, "--out", str(made)]) == 0
    none.write_text("", encoding="utf-8")
    capsys.readouterr()
    assert main(["stats", REFUND, str(none), "--pool", str(again), str(made)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[1:3] == [
        "records: 1 run, 0 calls, and 8 calls pooled from 1 other frames",
        "input no-receipt",
    ]
    assert not any(line.startswith("agreement") for line in lines)


def test_portfolio_names_shared_obligations_and_inputs_that_disagree(tmp_path, capsys):
    gap = "no hidden fallback (no bypass trial was declared)"
    documents = {
        "a": {"category": "unresolved", "inputs": {"x1": "unresolved"}, "obligations": [gap]},
        "b": {
            "category": "unresolved",
            "inputs": {"x1": "carried", "x2": "cooled"},
            "obligations": [gap, "another check"],
        },
    }
    reports = []
    for name, overall in documents.items():
        reports.append(tmp_path / f"{name}.json")
        reports[-1].write_text(json.dumps({"frame": name, "overall": overall}), encoding="utf-8")
    assert main(["portfolio", *map(str, reports)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "2 frames",
        "unresolved: a, b",
        "open in several frames:",
        f"  {gap} (a, b)",
        "frames whose inputs disagree:",
        "  b: x1 carried, x2 cooled",
    ]


def test_a_positional_argument_no_command_takes_is_that_commands_mistake(capsys):
    assert main(["plan", REFUND, "extra.json"]) == 2
    assert capsys.readouterr().err.splitlines() == [
        "UsageError: unrecognized arguments extra.json",
        "gadfly plan --help shows its arguments",
    ]


def test_a_withhold_set_from_a_terminal_is_refused_not_waited_on(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", Terminal())
    assert main(["check-frame", REFUND, "--withhold", "-"]) == 2
    assert capsys.readouterr().err.splitlines() == [
        "UsageError: - reads standard input, which is a terminal",
        "pipe the file in, or name it",
    ]


# ---- firm


@pytest.fixture
def thrice(tmp_path):
    # the refund frame asked three times a trial, as asking until firm needs,
    # and an empty folder for its runs
    raw = json.loads(Path(REFUND).read_text(encoding="utf-8"))
    raw["standing"] = {"quorum": 3, "agree": 2}
    frame = tmp_path / "refund.json"
    frame.write_text(json.dumps(raw), encoding="utf-8")
    (tmp_path / "runs").mkdir()
    return frame, tmp_path / "runs"


def firm(frame, runs, reader, *more):
    battery = f"tests.fixtures.refund:{reader}"
    return main(["firm", str(frame), "--battery", battery, "--runs", str(runs), *more])


def test_firm_shows_another_librarys_warning_as_python_would_in_process(thrice, capsys):
    frame, runs = thrice
    with pytest.warns(UserWarning, match="^a library of the reader's warned$"):
        assert firm(frame, runs, "Warned", "--calls", "100") == 0
    assert capsys.readouterr().err == ""


def test_firm_says_some_calls_opened_without_calling_the_run_unread(thrice, capsys):
    # an opening among answers is said, but the run was read: no note to ask again
    frame, runs = thrice
    assert firm(frame, runs, "OnceUnreachable", "--calls", "100") == 0
    told = capsys.readouterr()
    assert told.out.splitlines()[-1].startswith("firm: yes, carried after 2 runs")
    assert told.err.splitlines() == [
        "OpeningWarning: 1 of 24 calls came back as openings, most often "
        "'the reader could not be reached (ConnectionRefused)' once"
    ]


def test_firm_names_no_step_when_every_trial_read_the_one_made(tmp_path, capsys):
    from tests.fixtures.needs import NEEDS

    frame, runs = tmp_path / "needs.json", tmp_path / "runs"
    frame.write_text(json.dumps(NEEDS), encoding="utf-8")
    runs.mkdir()
    battery = ["--battery", "tests.fixtures.needs:branch", "--output-tokens", "100"]
    argv = ["firm", str(frame), *battery, "--runs", str(runs), "--calls", "auto", "--most", "2"]
    assert main([*argv, "--json"]) == 0
    read = json.loads(capsys.readouterr().out)
    assert [entry["remade"] for entry in read["steps"].values()] == [[]]
    (runs / "1.jsonl").rename(tmp_path / "first.jsonl")
    assert main(argv) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[-1].startswith("firm: yes, ") and not any(
        line.startswith("steps:") for line in lines
    )


# ---- the command run as the program


@pytest.fixture
def program(monkeypatch):
    """main() as the program runs it, its arguments from sys.argv; the SIGPIPE
    handler it sets is put back after."""
    pipe = getattr(signal, "SIGPIPE", None)
    before = signal.getsignal(pipe) if pipe else None

    def given(*argv):
        monkeypatch.setattr("sys.argv", ["gadfly", *argv])

    yield given
    if pipe:
        signal.signal(pipe, before)


def test_as_the_program_its_output_is_utf8_and_sigpipe_ends_it(tmp_path, program, monkeypatch):
    # standard output on a code page with no ✓, as a Windows pipe gives it
    # before Python 3.15; standard error a stream of the caller's own
    frame = json.loads(Path(REFUND).read_text(encoding="utf-8"))
    frame["interventions"]["presentation"] = {"receipt": "proof ✓"}
    (tmp_path / "frame.json").write_text(json.dumps(frame), encoding="utf-8")
    written = io.BytesIO()
    monkeypatch.setattr("sys.stdout", io.TextIOWrapper(written, encoding="cp1252"))
    monkeypatch.setattr("sys.stderr", io.StringIO())
    program("plan", str(tmp_path / "frame.json"))
    assert main() == 0
    sys.stdout.flush()
    assert "renames receipt to proof ✓" in written.getvalue().decode("utf-8")
    assert sys.stderr.getvalue() == ""
    if hasattr(signal, "SIGPIPE"):  # a reader that stops reading ends it, as any Unix tool
        assert signal.getsignal(signal.SIGPIPE) == signal.SIG_DFL


@pytest.mark.parametrize("platform", ["with its own SIGPIPE", "with none, as Windows"])
def test_as_the_program_it_lets_sigpipe_end_it_on_every_platform(
    platform, program, monkeypatch, capsys
):
    # Windows has no SIGPIPE, so a stand-in lets the line that sets it run
    # there too; the handlers it sets are recorded, not set on this process
    stand_in = getattr(signal, "SIGPIPE", 13)
    if platform.endswith("Windows"):
        monkeypatch.delattr(signal, "SIGPIPE", raising=False)
    monkeypatch.setattr(signal, "SIGPIPE", stand_in, raising=False)
    set_to = []
    monkeypatch.setattr(signal, "signal", lambda signum, handler: set_to.append((signum, handler)))
    program("plan", REFUND)
    assert main() == 0
    assert (stand_in, signal.SIG_DFL) in set_to
    assert ": 8 calls" in capsys.readouterr().out


def test_as_the_program_a_gone_reader_is_sent_nothing_more(tmp_path, capsys, program, monkeypatch):
    # where no SIGPIPE ends it, what is left unwritten goes to the null device
    class Gone(io.StringIO):
        def __init__(self, fd):
            super().__init__()
            self.fd = fd

        def write(self, text):
            raise BrokenPipeError(errno.EPIPE, "Broken pipe")

        def fileno(self):
            return self.fd

    sink = tmp_path / "sink"
    fd = os.open(sink, os.O_WRONLY | os.O_CREAT)
    try:
        monkeypatch.setattr("sys.stdout", Gone(fd))
        program("plan", REFUND)
        assert main() == 141
        os.write(fd, b"left unwritten")  # as the flush at exit would
    finally:
        os.close(fd)
    assert sink.read_bytes() == b"" and capsys.readouterr().err == ""


def test_python_m_midwife_cli_is_the_command_line_too(capsys, program, monkeypatch):
    program("plan", REFUND)
    monkeypatch.delitem(sys.modules, "midwife.cli")  # run afresh, as python -m runs it
    with pytest.raises(SystemExit) as ended:
        runpy.run_module("midwife.cli", run_name="__main__")
    assert ended.value.code == 0
    assert ": 8 calls" in capsys.readouterr().out.splitlines()[0]


# ---- a folder that cannot be written, on every platform


@pytest.fixture
def unwritable(monkeypatch):
    """A folder the system says cannot be written: chmod takes no folder's
    write bit on Windows, so os.access answers for it here, everywhere."""
    folders, asked = [], os.access

    def access(path, mode, *args, **kwargs):
        if mode == os.W_OK and Path(path) in folders:
            return False
        return asked(path, mode, *args, **kwargs)

    monkeypatch.setattr(os, "access", access)
    return folders.append


def test_an_unwritable_folder_for_the_records_is_refused_everywhere(tmp_path, unwritable, capsys):
    folder = tmp_path / "kept"
    folder.mkdir()
    unwritable(folder)
    assert main(["run", REFUND, *RULES, "--out", str(folder / "records.jsonl")]) == 7
    assert capsys.readouterr().err.splitlines()[-2:] == [
        f"PermissionError: folder {str(folder)!r} cannot be written",
        "choose another --out",
    ]
    assert list(folder.iterdir()) == []


def test_an_unwritable_runs_folder_is_refused_by_firm_everywhere(tmp_path, unwritable, capsys):
    raw = json.loads(Path(REFUND).read_text(encoding="utf-8"))
    raw["standing"] = {"quorum": 3, "agree": 2}
    frame, runs = tmp_path / "refund.json", tmp_path / "runs"
    frame.write_text(json.dumps(raw), encoding="utf-8")
    runs.mkdir()
    unwritable(runs)
    battery = ["--battery", "tests.fixtures.refund:RuleReader", "--calls", "100"]
    assert main(["firm", str(frame), *battery, "--runs", str(runs)]) == 7
    assert capsys.readouterr().err.splitlines()[-2:] == [
        f"PermissionError: folder {str(runs)!r} cannot be written",
        "choose another --runs",
    ]
    assert list(runs.iterdir()) == []
