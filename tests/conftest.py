"""A small public frame every test starts from: a refund policy whose second
rule is the premise under test."""

import copy

import pytest

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
    "body": {
        "spans": [
            {"id": "r1", "text": "Refunds are granted within 30 days of purchase.", "kind": "rule"},
            {"id": "r2", "text": "A refund requires a receipt.", "kind": "rule"},
            {"id": "r3", "text": "Gift cards are never refunded.", "kind": "rule"},
            {"id": "r4", "text": "Refunds go back to the original payment.", "kind": "rule"},
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
        "bypass": ["r2"],
    },
    "allowed": {"ablation": ["grant", "unclear"]},
    "standing": {"quorum": 3, "agree": 2},
    "battery": {"kind": "unified", "model": "anthropic/claude-sonnet-5-5"},
}


@pytest.fixture
def raw():
    return copy.deepcopy(REFUND)
