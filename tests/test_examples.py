"""The refund example, as a user runs it."""

import pytest

from examples import refund


def test_presentation_tells_a_phrase_from_a_rule(tmp_path):
    findings = refund.main(tmp_path / "records.jsonl")
    assert [(name, category) for name, category, _ in findings] == [
        ("phrase-matcher", "coupled but misaligned"),
        ("rule-reader", "carried"),
    ]
    assert findings[0][2] == ["presentation moved it decline -> grant"]
    assert findings[1][2] == [
        "ablation moved it decline -> grant, and it held under presentation and the sham"
    ]


def test_the_example_never_writes_over_kept_records(tmp_path):
    kept = tmp_path / "records.jsonl"
    kept.write_text("")
    with pytest.raises(FileExistsError):
        refund.main(kept)
