from prguard.git.diff import ChangedFile
from prguard.review.engine import (
    ReviewSummary,
)


def test_review_summary_counts_files():
    summary = ReviewSummary(
        branch="feature/test",
        base_ref="main",
        changed_files=[
            ChangedFile(
                path="one.py",
                changed_lines={
                    1,
                    2,
                },
            ),
            ChangedFile(
                path="two.swift",
                changed_lines={
                    10,
                },
            ),
        ],
        issues=[],
    )

    assert summary.file_count == 2


def test_review_summary_counts_changed_lines():
    summary = ReviewSummary(
        branch="feature/test",
        base_ref="main",
        changed_files=[
            ChangedFile(
                path="one.py",
                changed_lines={
                    1,
                    2,
                    3,
                },
            ),
            ChangedFile(
                path="two.java",
                changed_lines={
                    10,
                    11,
                },
            ),
        ],
        issues=[],
    )

    assert (
        summary.changed_line_count
        == 5
    )