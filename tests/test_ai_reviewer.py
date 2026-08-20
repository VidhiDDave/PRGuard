import json
from types import SimpleNamespace

import pytest

from prguard.ai.reviewer import (
    AIReviewError,
    _build_changed_context,
    _parse_ai_findings,
    review_with_ai,
)
from prguard.git import ChangedFile
from prguard.models import Severity


class FakeResponses:
    def __init__(
        self,
        output_text: str,
    ):
        self.output_text = output_text
        self.last_request = None

    def create(
        self,
        **kwargs,
    ):
        self.last_request = kwargs

        return SimpleNamespace(
            output_text=self.output_text
        )


class FakeClient:
    def __init__(
        self,
        output_text: str,
    ):
        self.responses = FakeResponses(
            output_text
        )


def test_parse_valid_ai_finding():
    changed_files = [
        ChangedFile(
            path="example.py",
            changed_lines={
                5,
            },
        )
    ]

    response = json.dumps(
        [
            {
                "severity": "high",
                "file_path": "example.py",
                "line": 5,
                "message": "Possible bug.",
                "suggestion": "Fix it.",
            }
        ]
    )

    issues = _parse_ai_findings(
        response,
        changed_files,
    )

    assert len(issues) == 1
    assert issues[0].severity == Severity.HIGH
    assert issues[0].line == 5


def test_rejects_ai_finding_on_unchanged_line():
    changed_files = [
        ChangedFile(
            path="example.py",
            changed_lines={
                5,
            },
        )
    ]

    response = json.dumps(
        [
            {
                "severity": "high",
                "file_path": "example.py",
                "line": 20,
                "message": "Possible bug.",
                "suggestion": "Fix it.",
            }
        ]
    )

    issues = _parse_ai_findings(
        response,
        changed_files,
    )

    assert issues == []


def test_rejects_unknown_file():
    changed_files = [
        ChangedFile(
            path="example.py",
            changed_lines={
                5,
            },
        )
    ]

    response = json.dumps(
        [
            {
                "severity": "high",
                "file_path": "other.py",
                "line": 5,
                "message": "Possible bug.",
                "suggestion": "Fix it.",
            }
        ]
    )

    issues = _parse_ai_findings(
        response,
        changed_files,
    )

    assert issues == []


def test_invalid_json_raises_error():
    changed_files = [
        ChangedFile(
            path="example.py",
            changed_lines={
                5,
            },
        )
    ]

    with pytest.raises(
        AIReviewError
    ):
        _parse_ai_findings(
            "not-json",
            changed_files,
        )


def test_ai_response_must_be_array():
    changed_files = [
        ChangedFile(
            path="example.py",
            changed_lines={
                5,
            },
        )
    ]

    with pytest.raises(
        AIReviewError
    ):
        _parse_ai_findings(
            "{}",
            changed_files,
        )


def test_context_only_contains_changed_lines(
    tmp_path,
    monkeypatch,
):
    source_file = (
        tmp_path
        / "example.py"
    )

    source_file.write_text(
        "\n".join(
            [
                "line one",
                "line two",
                "line three",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(
        tmp_path
    )

    context = _build_changed_context(
        [
            ChangedFile(
                path="example.py",
                changed_lines={
                    2,
                },
            )
        ],
        max_changed_lines=10,
    )

    assert "2: line two" in context
    assert "1: line one" not in context
    assert "3: line three" not in context


def test_context_respects_line_limit(
    tmp_path,
    monkeypatch,
):
    source_file = (
        tmp_path
        / "example.py"
    )

    source_file.write_text(
        "\n".join(
            [
                "one",
                "two",
                "three",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(
        tmp_path
    )

    context = _build_changed_context(
        [
            ChangedFile(
                path="example.py",
                changed_lines={
                    1,
                    2,
                    3,
                },
            )
        ],
        max_changed_lines=2,
    )

    assert "1: one" in context
    assert "2: two" in context
    assert "3: three" not in context


def test_review_with_ai_uses_fake_client(
    tmp_path,
    monkeypatch,
):
    source_file = (
        tmp_path
        / "example.py"
    )

    source_file.write_text(
        "dangerous_call()\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(
        tmp_path
    )

    response = json.dumps(
        [
            {
                "severity": "warning",
                "file_path": "example.py",
                "line": 1,
                "message": "Review this call.",
                "suggestion": "Validate behavior.",
            }
        ]
    )

    client = FakeClient(
        response
    )

    issues = review_with_ai(
        changed_files=[
            ChangedFile(
                path="example.py",
                changed_lines={
                    1,
                },
            )
        ],
        model="test-model",
        max_changed_lines=50,
        client=client,
    )

    assert len(issues) == 1

    assert (
        issues[0].rule_id
        == "ai-context-review"
    )

    assert (
        client.responses
        .last_request["model"]
        == "test-model"
    )


def test_empty_changed_files_skips_ai():
    client = FakeClient(
        "[]"
    )

    issues = review_with_ai(
        changed_files=[],
        model="test-model",
        max_changed_lines=50,
        client=client,
    )

    assert issues == []


def test_invalid_severity_is_ignored():
    changed_files = [
        ChangedFile(
            path="example.py",
            changed_lines={
                1,
            },
        )
    ]

    response = json.dumps(
        [
            {
                "severity": "dangerous",
                "file_path": "example.py",
                "line": 1,
                "message": "Bad.",
                "suggestion": "Fix.",
            }
        ]
    )

    issues = _parse_ai_findings(
        response,
        changed_files,
    )

    assert issues == []