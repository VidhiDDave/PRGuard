import json

from prguard.models import Severity
from prguard.review import ReviewSummary


def summary_to_dict(
    summary: ReviewSummary,
    fail_on: Severity,
    config_path: str,
    use_ai: bool,
) -> dict:
    blocking_issues = (
        summary.blocking_issues(
            fail_on
        )
    )

    return {
        "branch": summary.branch,
        "base": summary.base_ref,
        "configuration": config_path,
        "failure_threshold": (
            fail_on.label
        ),
        "ai_enabled": use_ai,
        "result": (
            "pass"
            if not blocking_issues
            else "fail"
        ),
        "supported_files_changed": (
            summary.file_count
        ),
        "changed_lines": (
            summary.changed_line_count
        ),
        "issue_count": (
            summary.issue_count
        ),
        "blocking_issue_count": len(
            blocking_issues
        ),
        "severity_counts": {
            "critical": (
                summary.count_by_severity(
                    Severity.CRITICAL
                )
            ),
            "high": (
                summary.count_by_severity(
                    Severity.HIGH
                )
            ),
            "warning": (
                summary.count_by_severity(
                    Severity.WARNING
                )
            ),
            "info": (
                summary.count_by_severity(
                    Severity.INFO
                )
            ),
        },
        "files": [
            {
                "path": changed_file.path,
                "language": (
                    changed_file.language
                ),
                "changed_lines": len(
                    changed_file.changed_lines
                ),
            }
            for changed_file
            in summary.changed_files
        ],
        "issues": [
            {
                "rule_id": issue.rule_id,
                "severity": (
                    issue.severity.label
                ),
                "file_path": (
                    issue.file_path
                ),
                "line": issue.line,
                "category": (
                    issue.category
                ),
                "message": (
                    issue.message
                ),
                "suggestion": (
                    issue.suggestion
                ),
            }
            for issue in summary.issues
        ],
    }


def render_json(
    summary: ReviewSummary,
    fail_on: Severity,
    config_path: str,
    use_ai: bool,
) -> str:
    data = summary_to_dict(
        summary=summary,
        fail_on=fail_on,
        config_path=config_path,
        use_ai=use_ai,
    )

    return json.dumps(
        data,
        indent=2,
        sort_keys=True,
    )