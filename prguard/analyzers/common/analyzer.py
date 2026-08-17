import re

from prguard.models import Issue, Severity


_AWS_ACCESS_KEY_PATTERN = re.compile(
    r"\bAKIA[0-9A-Z]{16}\b"
)

_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN "
    r"(?:RSA |EC |OPENSSH )?"
    r"PRIVATE KEY-----"
)

_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"""
    \b
    (
        api[_-]?key
        |
        secret
        |
        access[_-]?token
        |
        auth[_-]?token
        |
        password
    )
    \b
    \s*
    (?:
        =
        |
        :
    )
    \s*
    ["']
    ([^"']{8,})
    ["']
    """,
    re.IGNORECASE | re.VERBOSE,
)

_TODO_PATTERN = re.compile(
    r"\b(TO"
    r"DO|FIX"
    r"ME)\b",
    re.IGNORECASE,
)


class CommonAnalyzer:
    def __init__(
        self,
        file_path: str,
        source: str,
        language: str,
    ):
        self.file_path = file_path
        self.lines = source.splitlines()
        self.language = language
        self.issues: list[Issue] = []

    def analyze(self) -> list[Issue]:
        for line_number, line in enumerate(
            self.lines,
            start=1,
        ):
            self._check_aws_access_key(
                line_number,
                line,
            )

            self._check_private_key(
                line_number,
                line,
            )

            self._check_secret_assignment(
                line_number,
                line,
            )

            self._check_todo(
                line_number,
                line,
            )

            self._check_debug_output(
                line_number,
                line,
            )

        return self.issues

    def _add_issue(
        self,
        rule_id: str,
        severity: Severity,
        line: int,
        message: str,
        suggestion: str,
        category: str,
    ) -> None:
        self.issues.append(
            Issue(
                rule_id=rule_id,
                severity=severity,
                file_path=self.file_path,
                line=line,
                message=message,
                suggestion=suggestion,
                category=category,
            )
        )

    def _check_aws_access_key(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if _AWS_ACCESS_KEY_PATTERN.search(
            line
        ):
            self._add_issue(
                rule_id="common-aws-access-key",
                severity=Severity.CRITICAL,
                line=line_number,
                message=(
                    "Possible AWS access key is "
                    "hardcoded in source."
                ),
                suggestion=(
                    "Remove the credential, rotate it "
                    "if it is real, and load secrets "
                    "from secure configuration."
                ),
                category="security",
            )

    def _check_private_key(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if _PRIVATE_KEY_PATTERN.search(
            line
        ):
            self._add_issue(
                rule_id="common-private-key",
                severity=Severity.CRITICAL,
                line=line_number,
                message=(
                    "Private-key material appears "
                    "to be committed."
                ),
                suggestion=(
                    "Remove the private key from the "
                    "repository and rotate it if it "
                    "was exposed."
                ),
                category="security",
            )

    def _check_secret_assignment(
        self,
        line_number: int,
        line: str,
    ) -> None:
        match = _SECRET_ASSIGNMENT_PATTERN.search(
            line
        )

        if match is None:
            return

        value = match.group(2)

        if self._looks_like_placeholder(
            value
        ):
            return

        self._add_issue(
            rule_id="common-hardcoded-secret",
            severity=Severity.HIGH,
            line=line_number,
            message=(
                "Possible hardcoded credential "
                "or secret detected."
            ),
            suggestion=(
                "Move sensitive values into "
                "environment variables or a secure "
                "secret-management system."
            ),
            category="security",
        )

    def _check_todo(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if not _TODO_PATTERN.search(
            line
        ):
            return

        self._add_issue(
            rule_id="common-todo-fixme",
            severity=Severity.INFO,
            line=line_number,
            message=(
                "Unfinished-work marker was added."
            ),
            suggestion=(
                "Confirm this work can safely remain "
                "unfinished before merging."
            ),
            category="maintenance",
        )

    def _check_debug_output(
        self,
        line_number: int,
        line: str,
    ) -> None:
        stripped = line.strip()

        if self.language == "swift":
            is_debug = (
                stripped.startswith(
                    "debugPrint("
                )
                or stripped.startswith(
                    "dump("
                )
            )

        elif self.language == "java":
            is_debug = (
                "System.out.println(" in stripped
                or "System.err.println(" in stripped
            )

        elif self.language == "python":
            is_debug = (
                stripped.startswith(
                    "breakpoint("
                )
                or stripped == "breakpoint()"
            )

        else:
            is_debug = False

        if not is_debug:
            return

        self._add_issue(
            rule_id="common-debug-output",
            severity=Severity.WARNING,
            line=line_number,
            message=(
                "Possible debugging code was added."
            ),
            suggestion=(
                "Remove temporary debugging output "
                "before merging if it is no longer "
                "needed."
            ),
            category="quality",
        )

    @staticmethod
    def _looks_like_placeholder(
        value: str,
    ) -> bool:
        normalized = value.lower()

        placeholders = (
            "example",
            "placeholder",
            "your_",
            "your-",
            "changeme",
            "dummy",
            "fake",
            "test",
        )

        return any(
            marker in normalized
            for marker in placeholders
        )


def analyze_common_source(
    file_path: str,
    source: str,
    language: str,
) -> list[Issue]:
    analyzer = CommonAnalyzer(
        file_path=file_path,
        source=source,
        language=language,
    )

    return analyzer.analyze()