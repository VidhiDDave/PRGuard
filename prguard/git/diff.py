import re
from dataclasses import dataclass
from pathlib import Path

from prguard.git.repository import run_git


SUPPORTED_EXTENSIONS = {
    ".py",
    ".swift",
    ".java",
}


@dataclass(frozen=True)
class ChangedFile:
    path: str
    changed_lines: set[int]

    @property
    def language(self) -> str | None:
        extension = Path(self.path).suffix.lower()

        if extension == ".py":
            return "python"

        if extension == ".swift":
            return "swift"

        if extension == ".java":
            return "java"

        return None


_HUNK_HEADER = re.compile(
    r"^@@ "
    r"-\d+(?:,\d+)? "
    r"\+(?P<start>\d+)"
    r"(?:,(?P<count>\d+))? "
    r"@@"
)


def parse_changed_lines(diff: str) -> set[int]:
    changed_lines: set[int] = set()

    for line in diff.splitlines():
        match = _HUNK_HEADER.match(line)

        if match is None:
            continue

        start = int(match.group("start"))
        count = int(
            match.group("count") or "1"
        )

        if count == 0:
            continue

        changed_lines.update(
            range(
                start,
                start + count,
            )
        )

    return changed_lines


def get_changed_file_paths(
    base_ref: str,
) -> list[str]:
    output = run_git(
        "diff",
        "--name-only",
        "--diff-filter=ACMR",
        f"{base_ref}...HEAD",
    )

    if not output:
        return []

    return [
        line
        for line in output.splitlines()
        if line.strip()
    ]


def get_changed_lines(
    base_ref: str,
    file_path: str,
) -> set[int]:
    output = run_git(
        "diff",
        "--unified=0",
        "--no-color",
        f"{base_ref}...HEAD",
        "--",
        file_path,
    )

    return parse_changed_lines(output)


def get_supported_changed_files(
    base_ref: str,
) -> list[ChangedFile]:
    changed_files: list[ChangedFile] = []

    for file_path in get_changed_file_paths(
        base_ref
    ):
        extension = Path(
            file_path
        ).suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            continue

        changed_files.append(
            ChangedFile(
                path=file_path,
                changed_lines=get_changed_lines(
                    base_ref,
                    file_path,
                ),
            )
        )

    return changed_files