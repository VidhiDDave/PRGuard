import argparse

from prguard import __version__
from prguard.ai import AIReviewError
from prguard.config import (
    DEFAULT_CONFIG_PATH,
    ConfigError,
    load_config,
)
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
        default=None,
        help=(
            "Override the configured lowest "
            "severity that causes the review "
            "to fail."
        ),
    )

    review_parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help=(
            "PRGuard TOML configuration file "
            "(default: .prguard.toml)."
        ),
    )

    ai_group = (
        review_parser
        .add_mutually_exclusive_group()
    )

    ai_group.add_argument(
        "--ai",
        dest="use_ai",
        action="store_true",
        help=(
            "Enable optional AI-assisted "
            "context review."
        ),
    )

    ai_group.add_argument(
        "--no-ai",
        dest="use_ai",
        action="store_false",
        help=(
            "Disable AI-assisted review."
        ),
    )

    review_parser.set_defaults(
        use_ai=None
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
    fail_on: Severity | None = None,
    config_path: str = DEFAULT_CONFIG_PATH,
    use_ai: bool | None = None,
) -> int:
    ensure_git_repository()

    config = load_config(
        config_path
    )

    effective_fail_on = (
        fail_on
        if fail_on is not None
        else config.fail_on
    )

    effective_use_ai = (
        use_ai
        if use_ai is not None
        else config.ai.enabled
    )

    summary = prepare_review(
        base,
        config=config,
        use_ai=effective_use_ai,
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
        f"Configuration: "
        f"{config_path}"
    )

    print(
        f"Failure threshold: "
        f"{effective_fail_on.label}"
    )

    print(
        f"AI review: "
        f"{'enabled' if effective_use_ai else 'disabled'}"
    )

    if effective_use_ai:
        print(
            f"AI model: "
            f"{config.ai.model}"
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
            "No enabled Python, Swift, "
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
        effective_fail_on,
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
            fail_on = None

            if args.fail_on is not None:
                fail_on = (
                    Severity.from_string(
                        args.fail_on
                    )
                )

            return run_review(
                base=args.base,
                fail_on=fail_on,
                config_path=args.config,
                use_ai=args.use_ai,
            )

    except GitError as error:
        print(
            f"PRGuard Git error: {error}"
        )

        return 2

    except ConfigError as error:
        print(
            f"PRGuard configuration error: "
            f"{error}"
        )

        return 2

    except AIReviewError as error:
        print(
            f"PRGuard AI review error: "
            f"{error}"
        )

        return 2

    return 0