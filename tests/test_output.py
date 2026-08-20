import json

from prguard.git import ChangedFile
from prguard.models import (
    Issue,
    Severity,
)
from prguard.output import (
    render_json,
    summary_to_dict,
)
from prguard.review import ReviewSummary


def make_issue(
    severity: Severity,
) -> Issue:
    return Issue(
        rule_id="test-rule",
        severity=severity,
        file_path="example.py",
        line=2,
        message="Test finding.",
        suggestion="Fix it.",
        category="correctness",
    )


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
                    2,
                },
            )
        ],
        issues=issues,
    )


def test_summary_to_dict_reports_pass():
    summary = make_summary(
        [
            make_issue(
                Severity.WARNING
            )
        ]
    )

    result = summary_to_dict(
        summary=summary,
        fail_on=Severity.HIGH,
        config_path=".prguard.toml",
        use_ai=False,
    )

    assert (
        result["result"]
        == "pass"
    )

    assert (
        result["blocking_issue_count"]
        == 0
    )


def test_summary_to_dict_reports_fail():
    summary = make_summary(
        [
            make_issue(
                Severity.HIGH
            )
        ]
    )

    result = summary_to_dict(
        summary=summary,
        fail_on=Severity.HIGH,
        config_path=".prguard.toml",
        use_ai=False,
    )

    assert (
        result["result"]
        == "fail"
    )

    assert (
        result["blocking_issue_count"]
        == 1
    )


def test_json_contains_issue_details():
    summary = make_summary(
        [
            make_issue(
                Severity.HIGH
            )
        ]
    )

    output = render_json(
        summary=summary,
        fail_on=Severity.HIGH,
        config_path=".prguard.toml",
        use_ai=False,
    )

    data = json.loads(
        output
    )

    issue = data["issues"][0]

    assert (
        issue["rule_id"]
        == "test-rule"
    )

    assert (
        issue["severity"]
        == "high"
    )

    assert (
        issue["file_path"]
        == "example.py"
    )

    assert issue["line"] == 2


def test_json_contains_file_information():
    summary = make_summary(
        []
    )

    output = render_json(
        summary=summary,
        fail_on=Severity.HIGH,
        config_path=".prguard.toml",
        use_ai=False,
    )

    data = json.loads(
        output
    )

    assert (
        data["files"][0]["path"]
        == "example.py"
    )

    assert (
        data["files"][0]["language"]
        == "python"
    )

    assert (
        data["files"][0]["changed_lines"]
        == 2
    )


def test_json_contains_severity_counts():
    summary = make_summary(
        [
            make_issue(
                Severity.CRITICAL
            ),
            make_issue(
                Severity.HIGH
            ),
            make_issue(
                Severity.WARNING
            ),
        ]
    )

    output = render_json(
        summary=summary,
        fail_on=Severity.HIGH,
        config_path=".prguard.toml",
        use_ai=False,
    )

    data = json.loads(
        output
    )

    assert (
        data["severity_counts"]["critical"]
        == 1
    )

    assert (
        data["severity_counts"]["high"]
        == 1
    )

    assert (
        data["severity_counts"]["warning"]
        == 1
    )


def test_json_records_ai_state():
    summary = make_summary(
        []
    )

    output = render_json(
        summary=summary,
        fail_on=Severity.HIGH,
        config_path=".prguard.toml",
        use_ai=True,
    )

    data = json.loads(
        output
    )

    assert (
        data["ai_enabled"]
        is True
    )