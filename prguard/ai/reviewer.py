import json
import os
from pathlib import Path

from prguard.git import ChangedFile
from prguard.models import Issue, Severity


class AIReviewError(RuntimeError):
    pass


def _severity_from_ai(
    value: str,
) -> Severity | None:
    try:
        return Severity.from_string(
            value
        )

    except ValueError:
        return None


def _build_changed_context(
    changed_files: list[ChangedFile],
    max_changed_lines: int,
) -> str:
    sections: list[str] = []
    remaining_lines = max_changed_lines

    for changed_file in changed_files:
        if remaining_lines <= 0:
            break

        path = Path(
            changed_file.path
        )

        if not path.exists():
            continue

        try:
            source_lines = path.read_text(
                encoding="utf-8"
            ).splitlines()

        except OSError:
            continue

        selected_lines: list[str] = []

        for line_number in sorted(
            changed_file.changed_lines
        ):
            if remaining_lines <= 0:
                break

            if (
                line_number <= 0
                or line_number > len(
                    source_lines
                )
            ):
                continue

            content = source_lines[
                line_number - 1
            ]

            selected_lines.append(
                f"{line_number}: {content}"
            )

            remaining_lines -= 1

        if not selected_lines:
            continue

        sections.append(
            "\n".join(
                [
                    (
                        f"FILE: "
                        f"{changed_file.path}"
                    ),
                    (
                        f"LANGUAGE: "
                        f"{changed_file.language}"
                    ),
                    "CHANGED LINES:",
                    *selected_lines,
                ]
            )
        )

    return "\n\n".join(
        sections
    )


def _build_prompt(
    context: str,
) -> str:
    return f"""
Review only the changed code below.

Look for contextual issues that deterministic static
checks may miss, including:

- correctness bugs
- unsafe assumptions
- resource or lifetime risks
- concurrency risks
- excessive or repeated API/network/database work
- error-handling weaknesses
- security risks
- important maintainability problems

Do not report formatting preferences or subjective style.

Only report an issue when the supplied changed code
provides enough evidence for a useful review finding.

Every finding MUST reference:
- an exact FILE shown below
- an exact changed LINE shown below

Return ONLY valid JSON.

The JSON must be an array.

Each element must have exactly these fields:

{{
  "severity": "info|warning|high|critical",
  "file_path": "path/from/context",
  "line": 123,
  "message": "concise explanation",
  "suggestion": "specific improvement"
}}

If there are no useful findings, return:

[]

Changed code:

{context}
""".strip()


def _parse_ai_findings(
    response_text: str,
    changed_files: list[ChangedFile],
) -> list[Issue]:
    try:
        raw_findings = json.loads(
            response_text
        )

    except json.JSONDecodeError as error:
        raise AIReviewError(
            "AI response was not valid JSON."
        ) from error

    if not isinstance(
        raw_findings,
        list,
    ):
        raise AIReviewError(
            "AI response must be a JSON array."
        )

    changed_by_path = {
        changed_file.path: changed_file
        for changed_file in changed_files
    }

    issues: list[Issue] = []

    for finding in raw_findings:
        if not isinstance(
            finding,
            dict,
        ):
            continue

        severity_value = finding.get(
            "severity"
        )

        file_path = finding.get(
            "file_path"
        )

        line = finding.get(
            "line"
        )

        message = finding.get(
            "message"
        )

        suggestion = finding.get(
            "suggestion"
        )

        if not isinstance(
            severity_value,
            str,
        ):
            continue

        severity = _severity_from_ai(
            severity_value
        )

        if severity is None:
            continue

        if not isinstance(
            file_path,
            str,
        ):
            continue

        changed_file = changed_by_path.get(
            file_path
        )

        if changed_file is None:
            continue

        if (
            not isinstance(
                line,
                int,
            )
            or isinstance(
                line,
                bool,
            )
        ):
            continue

        if line not in changed_file.changed_lines:
            continue

        if (
            not isinstance(
                message,
                str,
            )
            or not message.strip()
        ):
            continue

        if not isinstance(
            suggestion,
            str,
        ):
            suggestion = ""

        issues.append(
            Issue(
                rule_id="ai-context-review",
                severity=severity,
                file_path=file_path,
                line=line,
                message=message.strip(),
                suggestion=(
                    suggestion.strip()
                    or None
                ),
                category="ai-review",
            )
        )

    return issues


def review_with_ai(
    changed_files: list[ChangedFile],
    model: str,
    max_changed_lines: int,
    client=None,
) -> list[Issue]:
    if not changed_files:
        return []

    context = _build_changed_context(
        changed_files,
        max_changed_lines,
    )

    if not context:
        return []

    if client is None:
        if not os.environ.get(
            "OPENAI_API_KEY"
        ):
            raise AIReviewError(
                "AI review requires "
                "OPENAI_API_KEY."
            )

        try:
            from openai import OpenAI

        except ImportError as error:
            raise AIReviewError(
                "AI review requires the "
                "optional OpenAI dependency. "
                'Install with `pip install '
                '-e ".[ai]"`.'
            ) from error

        client = OpenAI()

    try:
        response = client.responses.create(
            model=model,
            instructions=(
                "You are a conservative "
                "software pull-request reviewer. "
                "Report only actionable issues "
                "supported by the supplied code."
            ),
            input=_build_prompt(
                context
            ),
            store=False,
        )

    except Exception as error:
        raise AIReviewError(
            f"AI review request failed: "
            f"{error}"
        ) from error

    response_text = getattr(
        response,
        "output_text",
        None,
    )

    if not isinstance(
        response_text,
        str,
    ):
        raise AIReviewError(
            "AI review returned no text output."
        )

    return _parse_ai_findings(
        response_text,
        changed_files,
    )