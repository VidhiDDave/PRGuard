# PRGuard

PRGuard is a pre-merge code review CLI for Python, Swift, and Java.

It analyzes only the changes introduced by a pull request or feature branch and reports potential correctness, stability, security, performance, concurrency, resource-management, and code-quality risks before merge.

PRGuard supports deterministic static review and optional AI-assisted contextual review.

## Features

- Python analysis
- Swift analysis
- Java analysis
- Cross-language safety checks
- Changed-line-only findings
- INFO, WARNING, HIGH, and CRITICAL severities
- Configurable merge-blocking threshold
- Hardcoded-secret detection
- Network and database call-in-loop detection
- Resource and concurrency risk detection
- Large PR and large file warnings
- Repository configuration through `.prguard.toml`
- Ignored paths and disabled rules
- Optional AI-assisted review
- User-provided OpenAI API key
- Text and JSON output
- GitHub manual merge gate
- Latest-commit status protection

## Requirements

- Python 3.11 or newer
- Git

## Installation

Clone the repository:

```bash
git clone https://github.com/VidhiDDave/PRGuard.git
cd PRGuard
```

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install PRGuard:

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

For optional AI review:

```bash
pip install -e ".[ai]"
```

For development with AI support:

```bash
pip install -e ".[dev,ai]"
```

## Basic Usage

Review the current branch against `main`:

```bash
prguard review --base main
```

PRGuard only reports issues associated with changed lines in supported source files.

Supported languages:

- Python
- Swift
- Java

## Severity Levels

PRGuard uses four severities:

```text
INFO
WARNING
HIGH
CRITICAL
```

The default failure threshold is:

```text
HIGH
```

Therefore:

```text
INFO      → reported, does not block
WARNING   → reported, does not block
HIGH      → blocks
CRITICAL  → blocks
```

Override the threshold:

```bash
prguard review --base main --fail-on warning
```

## Exit Codes

PRGuard uses exit codes suitable for automation:

```text
0 = review passed
1 = blocking findings were detected
2 = PRGuard could not complete the review
```

## Configuration

Add `.prguard.toml` to the repository root:

```toml
[review]
fail_on = "high"
disabled_rules = []
ignored_paths = []

[languages]
python = true
swift = true
java = true

[ai]
enabled = false
model = "gpt-5.5"
max_changed_lines = 400
```

### Disable Rules

Example:

```toml
[review]
disabled_rules = [
    "common-todo-fixme",
]
```

### Ignore Paths

Example:

```toml
[review]
ignored_paths = [
    "generated/**",
    "vendor/**",
]
```

### Disable a Language

Example:

```toml
[languages]
python = true
swift = true
java = false
```

## Deterministic Review

AI is optional.

Force deterministic-only review:

```bash
prguard review --base main --no-ai
```

No OpenAI API key is required.

## AI-Assisted Review

AI-assisted review runs after deterministic analysis and looks for contextual issues that static rules may not detect.

Enable it for one run:

```bash
prguard review --base main --ai
```

The user or repository running PRGuard supplies its own OpenAI API key.

Set it locally:

```bash
export OPENAI_API_KEY="your-key"
```

Do not commit API keys into source code or `.prguard.toml`.

PRGuard sends only capped changed-code context rather than the entire repository by default.

AI findings are accepted only when they reference an actual changed file and changed line.

AI is disabled by default.

## JSON Output

For machine-readable output:

```bash
prguard review \
  --base main \
  --no-ai \
  --format json
```

Example structure:

```json
{
  "result": "pass",
  "failure_threshold": "high",
  "ai_enabled": false,
  "issue_count": 2,
  "blocking_issue_count": 0,
  "severity_counts": {
    "critical": 0,
    "high": 0,
    "warning": 2,
    "info": 0
  }
}
```

PRGuard keeps the same exit-code behavior when JSON output is used.

## GitHub Merge Gate

PRGuard includes two GitHub Actions workflows.

### Pending Gate

When a pull request is:

- opened
- reopened
- updated with a new commit

PRGuard assigns the latest PR head commit:

```text
PRGuard — Pending
```

The analysis itself does not automatically run.

### Manual Review

When the developer is ready:

1. Open the repository's **Actions** tab.
2. Select **PRGuard Manual Review**.
3. Choose **Run workflow**.
4. Enter the pull request number.
5. Choose whether AI review should run.
6. Start the workflow.

PRGuard then reviews the latest head commit.

A passing review publishes:

```text
PRGuard — Success
```

A failing review publishes:

```text
PRGuard — Failure
```

A new commit receives a new pending status and must be reviewed again.

## Making PRGuard Required

In GitHub repository rules or branch protection, enable required status checks and require:

```text
PRGuard
```

This creates the intended workflow:

```text
PR opened
    ↓
PRGuard pending
    ↓
Developer finishes work
    ↓
Manual PRGuard review
    ↓
PASS
    ↓
PRGuard success
    ↓
Merge allowed
```

## GitHub AI Setup

For AI-assisted GitHub reviews, add this repository Actions secret:

```text
OPENAI_API_KEY
```

The repository owner provides the key.

PRGuard does not provide or centrally fund API usage.

Deterministic mode works without this secret.

## Security Model

The GitHub manual-review workflow uses the trusted base-branch version of PRGuard to review the pull request.

The pull request's version of PRGuard is not installed or executed.

The trusted base-branch `.prguard.toml` configuration is also used for enforcement.

This prevents a pull request from weakening PRGuard rules or modifying PRGuard itself to approve its own changes before those changes are merged.

## Example Findings

Python:

```text
python-mutable-default
python-bare-except
python-network-call-in-loop
python-blocking-sleep-in-async
python-subprocess-shell
```

Swift:

```text
swift-force-try
swift-force-cast
swift-force-unwrap
swift-unowned-self
swift-main-queue-sync
swift-network-call-in-loop
```

Java:

```text
java-empty-catch
java-broad-exception
java-runtime-exec
java-network-call-in-loop
java-database-call-in-loop
```

Cross-language:

```text
common-aws-access-key
common-private-key
common-hardcoded-secret
common-todo-fixme
common-debug-output
```

## Testing

Run the test suite:

```bash
pytest
```

Compile-check the package:

```bash
python -m compileall prguard
```

Run PRGuard against itself:

```bash
prguard review --base main --no-ai
```

## Design Philosophy

PRGuard is intended to identify useful review risks, not claim certainty where static analysis cannot provide it.

For example, PRGuard may identify:

```text
Potential lifetime risk
Potential N+1 behavior
Potential main-thread deadlock
Potential excessive network requests
```

It should not claim it has definitively proven every memory leak, race condition, or runtime failure.

## License

PRGuard is available under the MIT License.