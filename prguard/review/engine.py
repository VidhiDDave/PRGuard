from dataclasses import dataclass
from pathlib import Path

from prguard.analyzers import (
    analyze_common_source,
    analyze_java_source,
    analyze_python_source,
    analyze_swift_source,
)
from prguard.config import ReviewConfig
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


LARGE_FILE_CHANGED_LINES = 500
LARGE_PR_CHANGED_LINES = 1500
LARGE_PR_FILE_COUNT = 20


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


def _filter_changed_files(
    changed_files: list[ChangedFile],
    config: ReviewConfig,
) -> list[ChangedFile]:
    filtered_files: list[ChangedFile] = []

    for changed_file in changed_files:
        language = changed_file.language

        if language is None:
            continue

        if not config.is_language_enabled(
            language
        ):
            continue

        if config.is_path_ignored(
            changed_file.path
        ):
            continue

        filtered_files.append(
            changed_file
        )

    return filtered_files


def _filter_enabled_issues(
    issues: list[Issue],
    config: ReviewConfig,
) -> list[Issue]:
    return [
        issue
        for issue in issues
        if config.is_rule_enabled(
            issue.rule_id
        )
    ]


def _analyze_file(
    changed_file: ChangedFile,
) -> list[Issue]:
    path = Path(
        changed_file.path
    )

    if not path.exists():
        return []

    source = path.read_text(
        encoding="utf-8"
    )

    language_issues: list[Issue]

    if changed_file.language == "python":
        language_issues = (
            analyze_python_source(
                changed_file.path,
                source,
            )
        )

    elif changed_file.language == "swift":
        language_issues = (
            analyze_swift_source(
                changed_file.path,
                source,
            )
        )

    elif changed_file.language == "java":
        language_issues = (
            analyze_java_source(
                changed_file.path,
                source,
            )
        )

    else:
        return []

    common_issues = analyze_common_source(
        changed_file.path,
        source,
        changed_file.language,
    )

    issues = (
        language_issues
        + common_issues
    )

    return [
        issue
        for issue in issues
        if issue.line
        in changed_file.changed_lines
    ]


def _large_file_issues(
    changed_files: list[ChangedFile],
) -> list[Issue]:
    issues: list[Issue] = []

    for changed_file in changed_files:
        changed_line_count = len(
            changed_file.changed_lines
        )

        if (
            changed_line_count
            < LARGE_FILE_CHANGED_LINES
        ):
            continue

        issues.append(
            Issue(
                rule_id=(
                    "review-large-file-change"
                ),
                severity=Severity.WARNING,
                file_path=changed_file.path,
                line=min(
                    changed_file.changed_lines,
                    default=1,
                ),
                message=(
                    f"This file contains "
                    f"{changed_line_count} changed "
                    "lines."
                ),
                suggestion=(
                    "Consider whether the change can "
                    "be split into smaller, easier-to-"
                    "review pieces."
                ),
                category="reviewability",
            )
        )

    return issues


def _large_pr_issues(
    changed_files: list[ChangedFile],
) -> list[Issue]:
    total_lines = sum(
        len(file.changed_lines)
        for file in changed_files
    )

    file_count = len(
        changed_files
    )

    if (
        total_lines
        < LARGE_PR_CHANGED_LINES
        and file_count
        < LARGE_PR_FILE_COUNT
    ):
        return []

    return [
        Issue(
            rule_id="review-large-pr",
            severity=Severity.WARNING,
            file_path="<pull-request>",
            line=1,
            message=(
                "This pull request is unusually "
                "large for a single review."
            ),
            suggestion=(
                "Consider splitting unrelated work "
                "into smaller pull requests when "
                "practical."
            ),
            category="reviewability",
        )
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
    config: ReviewConfig | None = None,
) -> ReviewSummary:
    active_config = (
        config
        if config is not None
        else ReviewConfig()
    )

    base_ref = resolve_base_ref(
        base
    )

    changed_files = (
        get_supported_changed_files(
            base_ref
        )
    )

    changed_files = (
        _filter_changed_files(
            changed_files,
            active_config,
        )
    )

    issues: list[Issue] = []

    for changed_file in changed_files:
        issues.extend(
            _analyze_file(
                changed_file
            )
        )

    issues.extend(
        _large_file_issues(
            changed_files
        )
    )

    issues.extend(
        _large_pr_issues(
            changed_files
        )
    )

    issues = _filter_enabled_issues(
        issues,
        active_config,
    )

    return ReviewSummary(
        branch=current_branch(),
        base_ref=base_ref,
        changed_files=changed_files,
        issues=_sort_issues(
            issues
        ),
    )