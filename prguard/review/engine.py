from dataclasses import dataclass

from prguard.git import (
    ChangedFile,
    current_branch,
    get_supported_changed_files,
    resolve_base_ref,
)


@dataclass(frozen=True)
class ReviewSummary:
    branch: str
    base_ref: str
    changed_files: list[ChangedFile]

    @property
    def file_count(self) -> int:
        return len(self.changed_files)

    @property
    def changed_line_count(self) -> int:
        return sum(
            len(file.changed_lines)
            for file in self.changed_files
        )


def prepare_review(
    base: str,
) -> ReviewSummary:
    base_ref = resolve_base_ref(
        base
    )

    return ReviewSummary(
        branch=current_branch(),
        base_ref=base_ref,
        changed_files=get_supported_changed_files(
            base_ref
        ),
    )