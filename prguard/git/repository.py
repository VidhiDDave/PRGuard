import subprocess


class GitError(RuntimeError):
    pass


def run_git(*args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )

    if process.returncode != 0:
        message = process.stderr.strip() or process.stdout.strip()

        raise GitError(
            message or f"git {' '.join(args)} failed"
        )

    return process.stdout.strip()


def ensure_git_repository() -> None:
    run_git(
        "rev-parse",
        "--show-toplevel",
    )


def current_branch() -> str:
    return run_git(
        "branch",
        "--show-current",
    )


def resolve_base_ref(base: str) -> str:
    candidates = [
        base,
        f"origin/{base}",
    ]

    for candidate in candidates:
        process = subprocess.run(
            [
                "git",
                "rev-parse",
                "--verify",
                candidate,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if process.returncode == 0:
            return candidate

    raise GitError(
        f"Could not find base branch '{base}'. "
        "Fetch the branch or provide a valid --base value."
    )