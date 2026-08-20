from prguard.cli import run_review
from prguard.config import ReviewConfig
from prguard.git import ChangedFile
from prguard.models import (
    Issue,
    Severity,
)
from prguard.review import ReviewSummary


def make_summary(
    issues: list[Issue],
) -> ReviewSummary:
    return ReviewSummary(
        branch="feature/test",
        base_ref="main",
        changed_files=[
            ChangedFile(
                path="example.py",
                changed_lines={
                    1,
                },
            )
        ],
        issues=issues,
    )


def make_issue(
    severity: Severity,
) -> Issue:
    return Issue(
        rule_id="test-rule",
        severity=severity,
        file_path="example.py",
        line=1,
        message="Test issue.",
        suggestion="Fix it.",
        category="correctness",
    )


def configure_test_review(
    monkeypatch,
    summary: ReviewSummary,
    config: ReviewConfig | None = None,
) -> None:
    monkeypatch.setattr(
        "prguard.cli.ensure_git_repository",
        lambda: None,
    )

    monkeypatch.setattr(
        "prguard.cli.load_config",
        lambda path: (
            config
            if config is not None
            else ReviewConfig()
        ),
    )

    monkeypatch.setattr(
        "prguard.cli.prepare_review",
        lambda base, config: summary,
    )


def test_review_returns_zero_when_no_blocking_issues(
    monkeypatch,
):
    summary = make_summary(
        [
            make_issue(
                Severity.WARNING
            )
        ]
    )

    configure_test_review(
        monkeypatch,
        summary,
    )

    result = run_review(
        "main",
        Severity.HIGH,
    )

    assert result == 0


def test_review_returns_one_for_high_issue(
    monkeypatch,
):
    summary = make_summary(
        [
            make_issue(
                Severity.HIGH
            )
        ]
    )

    configure_test_review(
        monkeypatch,
        summary,
    )

    result = run_review(
        "main",
        Severity.HIGH,
    )

    assert result == 1


def test_warning_can_be_configured_to_fail(
    monkeypatch,
):
    summary = make_summary(
        [
            make_issue(
                Severity.WARNING
            )
        ]
    )

    configure_test_review(
        monkeypatch,
        summary,
    )

    result = run_review(
        "main",
        Severity.WARNING,
    )

    assert result == 1


def test_configured_threshold_is_used(
    monkeypatch,
):
    summary = make_summary(
        [
            make_issue(
                Severity.WARNING
            )
        ]
    )

    config = ReviewConfig(
        fail_on=Severity.WARNING
    )

    configure_test_review(
        monkeypatch,
        summary,
        config,
    )

    result = run_review(
        "main"
    )

    assert result == 1


def test_cli_threshold_overrides_config(
    monkeypatch,
):
    summary = make_summary(
        [
            make_issue(
                Severity.WARNING
            )
        ]
    )

    config = ReviewConfig(
        fail_on=Severity.WARNING
    )

    configure_test_review(
        monkeypatch,
        summary,
        config,
    )

    result = run_review(
        "main",
        Severity.HIGH,
    )

    assert result == 0