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
from prguard.models import Issue


@dataclass(frozen=True)
class ReviewSummary:
    branch: str
    base_ref: str
    changed_files: list[ChangedFile]
    issues: list[Issue]

    @property
    def file_count(self) -> int:
        return len(self.changed_files)

    @property
    def changed_line_count(self) -> int:
        return sum(
            len(file.changed_lines)
            for file in self.changed_files
        )

    @property
    def issue_count(self) -> int:
        return len(self.issues)


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
        issues=issues,
    )