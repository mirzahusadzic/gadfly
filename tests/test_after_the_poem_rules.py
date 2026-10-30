"""The replay's conversion of the study's agreement threshold, without its data."""

import pytest

from examples.after_the_poem import agreement_count, frame_for
from gadfly.pipeline import situate


@pytest.mark.parametrize(
    "sessions, threshold, needed",
    # The study compares the agreeing share rounded half up to two decimals.
    [
        (3, 0.67, 2),
        (4, 0.67, 3),
        (5, 0.67, 4),
        (6, 0.67, 4),
        (7, 0.67, 5),
        (3, 1.0, 3),
        (4, 0.5, 2),
    ],
)
def test_agreement_is_counted_as_the_study_counts_it(sessions, threshold, needed):
    assert agreement_count(sessions, threshold) == needed


def test_the_frame_takes_the_studys_count():
    case = {"id": "c", "run_id": "r", "axis": "a", "ablated_lines": 4}
    pinned = {"model": "m", "reasoning": "x", "rubric_sha256": "h", "prompt_version": "p"}
    study = {"id": "s", "frame": {**pinned, "sessions": 5, "minimum_agreement": 0.67}}
    assert frame_for(case, study)["standing"]["agree"] == 4
    # the replay's frame is a frame Gadfly accepts, data or no data
    situate(frame_for(case, study))
