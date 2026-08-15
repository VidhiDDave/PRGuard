from dataclasses import dataclass
from pathlib import Path

from prguard.analyzers import (
    analyze_python_source,
)
from prguard.git import (
    ChangedFile,
    current_branch,
    get_supported_changed_files,
    resolve_base_ref,
)
from prguard.models import (
    Issue,
    Severity,
)


@dataclass(frozen=True)
class ReviewSummary:
    branch: str
    base_ref: str
    changed_files: list[ChangedFile]
    issues: list[Issue]

    @property
    def file_count(self) -> int:
        return len(
            self.changed_files
        )

    @property
    def changed_line_count(self) -> int:
        return sum(
            len(file.changed_lines)
            for file in self.changed_files
        )

    @property
    def issue_count(self) -> int:
        return len(
            self.issues
        )

    def count_by_severity(
        self,
        severity: Severity,
    ) -> int:
        return sum(
            1
            for issue in self.issues
            if issue.severity == severity
        )

    def blocking_issues(
        self,
        fail_on: Severity,
    ) -> list[Issue]:
        return [
            issue
            for issue in self.issues
            if issue.severity >= fail_on
        ]

    def passes(
        self,
        fail_on: Severity,
    ) -> bool:
        return not self.blocking_issues(
            fail_on
        )

    @property
    def highest_severity(
        self,
    ) -> Severity | None:
        if not self.issues:
            return None

        return max(
            issue.severity
            for issue in self.issues
        )


def _analyze_file(
    changed_file: ChangedFile,
) -> list[Issue]:
    if changed_file.language != "python":
        return []

    path = Path(
        changed_file.path
    )

    if not path.exists():
        return []

    source = path.read_text(
        encoding="utf-8"
    )

    issues = analyze_python_source(
        changed_file.path,
        source,
    )

    return [
        issue
        for issue in issues
        if issue.line
        in changed_file.changed_lines
    ]


def _sort_issues(
    issues: list[Issue],
) -> list[Issue]:
    return sorted(
        issues,
        key=lambda issue: (
            -issue.severity,
            issue.file_path,
            issue.line,
            issue.rule_id,
        ),
    )


def prepare_review(
    base: str,
) -> ReviewSummary:
    base_ref = resolve_base_ref(
        base
    )

    changed_files = (
        get_supported_changed_files(
            base_ref
        )
    )

    issues: list[Issue] = []

    for changed_file in changed_files:
        issues.extend(
            _analyze_file(
                changed_file
            )
        )

    return ReviewSummary(
        branch=current_branch(),
        base_ref=base_ref,
        changed_files=changed_files,
        issues=_sort_issues(
            issues
        ),
    )