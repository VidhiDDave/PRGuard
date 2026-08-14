from prguard.models import Issue, Severity


def test_issue_stores_review_information():
    issue = Issue(
        rule_id="example-rule",
        severity=Severity.HIGH,
        file_path="example.py",
        line=10,
        message="Example issue.",
        suggestion="Fix the example.",
        category="correctness",
    )

    assert issue.rule_id == "example-rule"
    assert issue.severity == Severity.HIGH
    assert issue.severity.label == "high"
    assert issue.file_path == "example.py"
    assert issue.line == 10