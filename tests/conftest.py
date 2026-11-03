"""A small public frame every test starts from: a refund policy whose second
rule is the premise under test."""

import copy
import sys

import pytest

# whether anything imported midwife before this file, which pytest loads once
# coverage has started: those modules' first lines would go unmeasured
IMPORTED_BEFORE = "midwife" in sys.modules


def pytest_configure(config):
    # a run warns of its openings and stops; tests that mean to hear them use
    # pytest.warns. Said here rather than in pyproject.toml, whose filter
    # would import midwife before coverage starts
    config.addinivalue_line("filterwarnings", "ignore::midwife.errors.GadflyWarning")


@pytest.fixture
def midwife_imported_before():
    """Whether midwife was imported before coverage began."""
    return IMPORTED_BEFORE


REFUND = {
    "name": "refund-receipt",
    "relation": "a refund requires a receipt",
    "locus": "the refund policy, rule 2",
    "role": "a support agent",
    "grain": "one rule",
    "purpose": "decide a refund request",
    "trajectory": "policy, agent's decision, reply to the customer",
    "crossing": "the agent's reply",
    "promise": "a request without a receipt is declined",
    "baseline": "the policy as written and one request; no rule changed",
    "body": {
        "spans": [
            {"id": "r1", "text": "Refunds are granted within 30 days of purchase.", "kind": "rule"},
            {"id": "r2", "text": "A refund requires a receipt.", "kind": "rule"},
            {"id": "r3", "text": "Gift cards are never refunded.", "kind": "rule"},
            {"id": "r4", "text": "Refunds go back to the original payment.", "kind": "rule"},
            {"id": "r5", "text": "These rules decide every request.", "kind": "note"},
        ]
    },
    "anchors": ["r2"],
    "inputs": [{"id": "x1", "text": "A customer without a receipt asks for a refund on day 3."}],
    "observe": {
        "labels": ["grant", "decline", "unclear"],
        "instruction": "Decide the request under the policy.",
    },
    "interventions": {
        "repeat": True,
        "ablation": True,
        "sham": {"draws": 2},
        "presentation": {"receipt": "proof of purchase"},
        "bypass": ["r5"],
    },
    "allowed": {"ablation": ["grant", "unclear"]},
    "standing": {"quorum": 3, "agree": 2},
    # The rule-order tests read every category, so the fixture lists open
    # checks beside them; the default, all-checks, has tests of its own.
    "carriage": "listed",
    "battery": {"kind": "unified", "model": "anthropic/claude-sonnet-5-5"},
}


@pytest.fixture
def raw():
    return copy.deepcopy(REFUND)
