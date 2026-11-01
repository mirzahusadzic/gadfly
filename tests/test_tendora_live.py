"""The tendora battery against Tendora's own engine server: a live run, made
only when asked. It needs Tendora's demo package, installed (`npm ci`) and
named in TENDORA_PACKAGE; TENDORA_ONLINE=1 adds the trials whose new texts
the engine reads through eGemma. The server runs on a copy of the bundled
demo (Apache-2.0), on a port of its own."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from midwife.batteries.tendora import Tendora
from midwife.pipeline import calls_needed, judge, run, situate
from midwife.types import Budget

PACKAGE = os.environ.get("TENDORA_PACKAGE")
ONLINE = os.environ.get("TENDORA_ONLINE") == "1"
FRAME = Path(__file__).parent / "fixtures" / "payments-notify-chain.json"

pytestmark = pytest.mark.skipif(
    not PACKAGE or shutil.which("node") is None,
    reason="a live engine run: name Tendora's demo package in TENDORA_PACKAGE",
)


@pytest.fixture
def engine(tmp_path):
    project = tmp_path / "payments-on-call"
    shutil.copytree(Path(PACKAGE) / "demo" / "payments-on-call", project)
    command = ["node", str(Path(PACKAGE) / "dist" / "bin" / "serve.mjs"), "--project", str(project)]
    command += ["--port", "0"] + ([] if ONLINE else ["--offline"])
    served = subprocess.Popen(command, stdout=subprocess.PIPE, text=True, cwd=PACKAGE)
    try:
        line = served.stdout.readline()
        found = re.search(r" at (http://\S+)", line)
        assert found, f"the server did not start: {line!r}"
        yield found.group(1)
    finally:
        served.terminate()
        served.wait(timeout=10)


def test_the_reference_frame_against_the_engine(engine):
    # the predictions written before any call: Sam wherever both rules stand,
    # open without them; offline, presentation is left out and listed
    raw = json.loads(FRAME.read_text(encoding="utf-8"))
    raw["battery"]["url"] = engine
    expected = {
        "baseline": "Sam",
        "repeat": "Sam",
        "ablation": "open",
        "sham-1": "Sam",
        "sham-2": "Sam",
        "placement": "Sam",
        "bypass": "open",
        "control": "open",
    }
    if ONLINE:
        expected["presentation"] = "Sam"
    else:
        del raw["interventions"]["presentation"]
        raw["carriage"] = "listed"
    frame = situate(raw)
    Tendora().check(frame)
    assert calls_needed(frame) == len(expected)
    result = run(frame, Tendora(), Budget(calls=calls_needed(frame)))
    assert {r.trial: r.observation for r in result.records} == expected
    assert all(r.served.startswith("tendora ") for r in result.records)
    [finding] = judge(frame, result.records)
    assert finding.category == "carried"


@pytest.mark.skipif(not ONLINE, reason="the inverted rule is a new text: TENDORA_ONLINE=1")
def test_the_restore_inversion_against_the_engine(engine):
    # Tendora's measured reference, read through the tendora battery: Yes
    # with approval and No without, turned by the inversion, open where the
    # rule is cut; written before this run, carried on both inputs
    raw = json.loads((Path(__file__).parent / "fixtures" / "restore-inversion.json").read_text())
    raw["battery"] = {"kind": "tendora", "url": engine}
    frame = situate(raw)
    Tendora().check(frame)
    result = run(frame, Tendora(), Budget(calls=calls_needed(frame)))
    findings = {f.input: f for f in judge(frame, result.records)}
    assert findings["approved"].levels == {
        "baseline": "Yes",
        "repeat": "Yes",
        "ablation": "open",
        "inversion": "No",
        "control": "open",
    }
    assert findings["not-approved"].levels["inversion"] == "Yes"
    assert {f.category for f in findings.values()} == {"carried"}


@pytest.mark.skipif(not ONLINE, reason="a turned question is a new text: TENDORA_ONLINE=1")
@pytest.mark.parametrize(
    "fixture, approved, refused",
    [("restore-case-inversion", "No", "Yes"), ("restore-question-inversion", "open", "open")],
)
def test_what_is_asked_turned_against_the_engine(engine, fixture, approved, refused):
    # Tendora's measured predictions, written before this run: the case
    # turned turns each answer; the question's description turned opens it
    raw = json.loads((Path(__file__).parent / "fixtures" / f"{fixture}.json").read_text())
    raw["battery"] = {"kind": "tendora", "url": engine}
    frame = situate(raw)
    Tendora().check(frame)
    result = run(frame, Tendora(), Budget(calls=calls_needed(frame)))
    findings = {f.input: f for f in judge(frame, result.records)}
    assert findings["approved"].levels["input-inversion"] == approved
    assert findings["not-approved"].levels["input-inversion"] == refused
    assert {f.category for f in findings.values()} == {"carried"}


@pytest.mark.skipif(ONLINE, reason="the package's kept reports were read offline")
def test_each_published_frame_reads_its_kept_findings(engine):
    # the frames and reports the package publishes for its demo, read again
    # at this server's port: the address is the one change, so the hash is
    # new, and every level, category, evidence line and obligation is kept
    published = Path(PACKAGE) / "evidence" / "payments-demo"
    paths = sorted((published / "frames").glob("tendora-*.json"))
    assert paths, f"no published frames under {published}"
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["battery"]["url"] = engine
        frame = situate(raw)
        Tendora().check(frame)
        result = run(frame, Tendora(), Budget(calls=calls_needed(frame)))
        kept = json.loads((published / "reports" / path.name).read_text(encoding="utf-8"))
        read = [finding.as_dict() for finding in judge(frame, result.records)]
        assert read == kept["findings"], path.name
