import argparse

from prguard import __version__
from prguard.git import (
    GitError,
    ensure_git_repository,
)
from prguard.models import Severity
from prguard.review import prepare_review


DEFAULT_FAIL_ON = Severity.HIGH


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
        help=(
            "Review changes against "
            "a base branch."
        ),
    )

    review_parser.add_argument(
        "--base",
        default="main",
        help=(
            "Base branch to compare against "
            "(default: main)."
        ),
    )

    review_parser.add_argument(
        "--fail-on",
        choices=[
            "info",
            "warning",
            "high",
            "critical",
        ],
        default="high",
        help=(
            "Lowest severity that causes "
            "the review to fail "
            "(default: high)."
        ),
    )

    return parser


def _print_files(
    summary,
) -> None:
    print()
    print("Files:")

    for changed_file in summary.changed_files:
        print(
            f"  {changed_file.path}"
            f" [{changed_file.language}]"
            f" - {len(changed_file.changed_lines)} "
            "changed lines"
        )


def _print_issue_counts(
    summary,
) -> None:
    print()
    print(
        f"Issues found: "
        f"{summary.issue_count}"
    )

    if summary.issue_count == 0:
        return

    print(
        "  "
        f"Critical: "
        f"{summary.count_by_severity(Severity.CRITICAL)}"
    )
    print(
        "  "
        f"High: "
        f"{summary.count_by_severity(Severity.HIGH)}"
    )
    print(
        "  "
        f"Warning: "
        f"{summary.count_by_severity(Severity.WARNING)}"
    )
    print(
        "  "
        f"Info: "
        f"{summary.count_by_severity(Severity.INFO)}"
    )


def _print_issues(
    summary,
) -> None:
    if not summary.issues:
        return

    print()

    for issue in summary.issues:
        print(
            f"[{issue.severity.label.upper()}] "
            f"{issue.file_path}:{issue.line}"
        )

        print(
            f"  {issue.rule_id}"
        )

        print(
            f"  {issue.message}"
        )

        if issue.suggestion:
            print(
                f"  Suggestion: "
                f"{issue.suggestion}"
            )

        print()


def _print_result(
    summary,
    fail_on: Severity,
) -> bool:
    passed = summary.passes(
        fail_on
    )

    blocking_count = len(
        summary.blocking_issues(
            fail_on
        )
    )

    print("-" * 50)

    if passed:
        print(
            "Result: PASS"
        )
        print(
            "No findings meet or exceed "
            f"the {fail_on.label} "
            "failure threshold."
        )

    else:
        print(
            "Result: FAIL"
        )
        print(
            f"{blocking_count} finding(s) "
            "meet or exceed the "
            f"{fail_on.label} "
            "failure threshold."
        )

    return passed


def run_review(
    base: str,
    fail_on: Severity = DEFAULT_FAIL_ON,
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
        f"Failure threshold: "
        f"{fail_on.label}"
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

        print()
        print("-" * 50)
        print(
            "Result: PASS"
        )

        return 0

    _print_files(
        summary
    )

    _print_issue_counts(
        summary
    )

    _print_issues(
        summary
    )

    passed = _print_result(
        summary,
        fail_on,
    )

    if passed:
        return 0

    return 1


def main() -> int:
    parser = build_parser()

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.command == "review":
            fail_on = Severity.from_string(
                args.fail_on
            )

            return run_review(
                args.base,
                fail_on,
            )

    except GitError as error:
        print(
            f"PRGuard Git error: {error}"
        )

        return 2

    return 0