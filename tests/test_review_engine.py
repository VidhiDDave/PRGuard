from prguard.git.diff import ChangedFile
from prguard.models import (
    Issue,
    Severity,
)
from prguard.review.engine import (
    ReviewSummary,
)


def make_issue(
    severity: Severity,
    line: int = 1,
) -> Issue:
    return Issue(
        rule_id="test-rule",
        severity=severity,
        file_path="example.py",
        line=line,
        message="Test issue.",
        suggestion="Fix it.",
        category="correctness",
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


def test_counts_issues_by_severity():
    summary = ReviewSummary(
        branch="feature/test",
        base_ref="main",
        changed_files=[],
        issues=[
            make_issue(
                Severity.HIGH,
                1,
            ),
            make_issue(
                Severity.HIGH,
                2,
            ),
            make_issue(
                Severity.WARNING,
                3,
            ),
        ],
    )

    assert (
        summary.count_by_severity(
            Severity.HIGH
        )
        == 2
    )

    assert (
        summary.count_by_severity(
            Severity.WARNING
        )
        == 1
    )


def test_high_issue_blocks_default_threshold():
    summary = ReviewSummary(
        branch="feature/test",
        base_ref="main",
        changed_files=[],
        issues=[
            make_issue(
                Severity.HIGH
            )
        ],
    )

    assert (
        summary.passes(
            Severity.HIGH
        )
        is False
    )


def test_warning_does_not_block_high_threshold():
    summary = ReviewSummary(
        branch="feature/test",
        base_ref="main",
        changed_files=[],
        issues=[
            make_issue(
                Severity.WARNING
            )
        ],
    )

    assert (
        summary.passes(
            Severity.HIGH
        )
        is True
    )


def test_warning_blocks_warning_threshold():
    summary = ReviewSummary(
        branch="feature/test",
        base_ref="main",
        changed_files=[],
        issues=[
            make_issue(
                Severity.WARNING
            )
        ],
    )

    assert (
        summary.passes(
            Severity.WARNING
        )
        is False
    )


def test_highest_severity():
    summary = ReviewSummary(
        branch="feature/test",
        base_ref="main",
        changed_files=[],
        issues=[
            make_issue(
                Severity.INFO
            ),
            make_issue(
                Severity.CRITICAL
            ),
            make_issue(
                Severity.WARNING
            ),
        ],
    )

    assert (
        summary.highest_severity
        == Severity.CRITICAL
    )


def test_highest_severity_is_none_without_issues():
    summary = ReviewSummary(
        branch="feature/test",
        base_ref="main",
        changed_files=[],
        issues=[],
    )

    assert (
        summary.highest_severity
        is None
    )