import argparse

from prguard import __version__
from prguard.git import (
    GitError,
    ensure_git_repository,
)
from prguard.review import prepare_review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prguard",
        description=(
            "Pre-merge code review for "
            "Swift, Python, and Java."
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"PRGuard {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
    )

    review_parser = subparsers.add_parser(
        "review",
        help="Review changes against a base branch.",
    )

    review_parser.add_argument(
        "--base",
        default="main",
        help=(
            "Base branch to compare against "
            "(default: main)."
        ),
    )

    return parser


def run_review(
    base: str,
) -> int:
    ensure_git_repository()

    summary = prepare_review(
        base
    )

    print("PRGuard Review")
    print("=" * 50)
    print(
        f"Branch: {summary.branch}"
    )
    print(
        f"Base: {summary.base_ref}"
    )
    print(
        f"Supported files changed: "
        f"{summary.file_count}"
    )
    print(
        f"Changed lines: "
        f"{summary.changed_line_count}"
    )

    if not summary.changed_files:
        print()
        print(
            "No changed Python, Swift, "
            "or Java files found."
        )
        return 0

    print()
    print("Files:")

    for changed_file in summary.changed_files:
        print(
            f"  {changed_file.path}"
            f" [{changed_file.language}]"
            f" - {len(changed_file.changed_lines)} "
            "changed lines"
        )

    return 0


def main() -> int:
    parser = build_parser()

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.command == "review":
            return run_review(
                args.base
            )

    except GitError as error:
        print(
            f"PRGuard Git error: {error}"
        )
        return 2

    return 0