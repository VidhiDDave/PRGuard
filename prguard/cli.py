import argparse

from prguard import __version__


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="prguard",
        description="Pre-merge code review for Swift, Python, and Java.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"PRGuard {__version__}",
    )

    parser.parse_args()

    print("PRGuard is ready.")

    return 0