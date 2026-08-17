import re

from prguard.models import Issue, Severity


_LOOP_PATTERN = re.compile(
    r"^\s*(for|while)\b"
)

_HTTP_PATTERNS = (
    ".execute(",
    ".send(",
    ".sendAsync(",
)

_DATABASE_PATTERNS = (
    ".executeQuery(",
    ".executeUpdate(",
    ".execute(",
)


class JavaAnalyzer:
    def __init__(
        self,
        file_path: str,
        source: str,
    ):
        self.file_path = file_path
        self.lines = source.splitlines()
        self.issues: list[Issue] = []

        self.brace_depth = 0
        self.loop_depths: list[int] = []

    def analyze(self) -> list[Issue]:
        for line_number, raw_line in enumerate(
            self.lines,
            start=1,
        ):
            line = self._strip_comment(
                raw_line
            )

            if not line.strip():
                self._update_braces(
                    line
                )
                continue

            self._check_empty_catch(
                line_number,
                line,
            )

            self._check_broad_exception(
                line_number,
                line,
            )

            self._check_system_exit(
                line_number,
                line,
            )

            self._check_thread_sleep(
                line_number,
                line,
            )

            self._check_runtime_exec(
                line_number,
                line,
            )

            self._check_insecure_url(
                line_number,
                line,
            )

            self._check_network_call_in_loop(
                line_number,
                line,
            )

            self._check_database_call_in_loop(
                line_number,
                line,
            )

            self._track_loop_start(
                line
            )

            self._update_braces(
                line
            )

            self._remove_finished_loops()

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

    def _check_empty_catch(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if re.search(
            r"catch\s*\([^)]*\)\s*\{\s*\}",
            line,
        ):
            self._add_issue(
                rule_id="java-empty-catch",
                severity=Severity.HIGH,
                line=line_number,
                message=(
                    "Exception is caught and ignored."
                ),
                suggestion=(
                    "Handle, log, or propagate the "
                    "exception instead of silently "
                    "discarding it."
                ),
                category="stability",
            )

    def _check_broad_exception(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if re.search(
            r"catch\s*\(\s*Exception\b",
            line,
        ):
            self._add_issue(
                rule_id="java-broad-exception",
                severity=Severity.WARNING,
                line=line_number,
                message=(
                    "Catching Exception may hide "
                    "unexpected failures."
                ),
                suggestion=(
                    "Catch the narrowest exception "
                    "types the operation expects."
                ),
                category="stability",
            )

    def _check_system_exit(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if "System.exit(" in line:
            self._add_issue(
                rule_id="java-system-exit",
                severity=Severity.WARNING,
                line=line_number,
                message=(
                    "System.exit terminates the JVM."
                ),
                suggestion=(
                    "Confirm process termination is "
                    "intentional and appropriate for "
                    "this code path."
                ),
                category="stability",
            )

    def _check_thread_sleep(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if "Thread.sleep(" in line:
            self._add_issue(
                rule_id="java-thread-sleep",
                severity=Severity.WARNING,
                line=line_number,
                message=(
                    "Thread.sleep blocks the current "
                    "thread."
                ),
                suggestion=(
                    "Prefer scheduling, asynchronous "
                    "coordination, or other non-blocking "
                    "approaches when possible."
                ),
                category="concurrency",
            )

    def _check_runtime_exec(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if re.search(
            r"Runtime\.getRuntime\(\)\.exec\s*\(",
            line,
        ):
            self._add_issue(
                rule_id="java-runtime-exec",
                severity=Severity.HIGH,
                line=line_number,
                message=(
                    "Runtime.exec launches an external "
                    "process and may be unsafe with "
                    "untrusted input."
                ),
                suggestion=(
                    "Prefer ProcessBuilder with explicit "
                    "arguments and validate external "
                    "input."
                ),
                category="security",
            )

    def _check_insecure_url(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if re.search(
            r'new\s+URL\s*\(\s*"http://',
            line,
        ):
            self._add_issue(
                rule_id="java-insecure-url",
                severity=Severity.WARNING,
                line=line_number,
                message=(
                    "HTTP URL uses an unencrypted "
                    "connection."
                ),
                suggestion=(
                    "Use HTTPS unless insecure "
                    "transport is explicitly required."
                ),
                category="security",
            )

    def _check_network_call_in_loop(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if not self.loop_depths:
            return

        if any(
            pattern in line
            for pattern in _HTTP_PATTERNS
        ):
            self._add_issue(
                rule_id="java-network-call-in-loop",
                severity=Severity.HIGH,
                line=line_number,
                message=(
                    "Network work occurs inside a loop "
                    "and may create excessive requests."
                ),
                suggestion=(
                    "Consider batching, caching, "
                    "deduplication, or bounded "
                    "concurrency."
                ),
                category="performance",
            )

    def _check_database_call_in_loop(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if not self.loop_depths:
            return

        if any(
            pattern in line
            for pattern in _DATABASE_PATTERNS
        ):
            self._add_issue(
                rule_id="java-database-call-in-loop",
                severity=Severity.HIGH,
                line=line_number,
                message=(
                    "Database operation occurs inside "
                    "a loop and may cause N+1 behavior."
                ),
                suggestion=(
                    "Consider batching the database "
                    "operation when possible."
                ),
                category="performance",
            )

    def _track_loop_start(
        self,
        line: str,
    ) -> None:
        if (
            _LOOP_PATTERN.search(line)
            and "{" in line
        ):
            self.loop_depths.append(
                self.brace_depth + 1
            )

    def _update_braces(
        self,
        line: str,
    ) -> None:
        self.brace_depth += (
            line.count("{")
            - line.count("}")
        )

    def _remove_finished_loops(
        self,
    ) -> None:
        self.loop_depths = [
            depth
            for depth in self.loop_depths
            if self.brace_depth >= depth
        ]

    @staticmethod
    def _strip_comment(
        line: str,
    ) -> str:
        in_string = False
        escaped = False

        for index, character in enumerate(
            line
        ):
            if escaped:
                escaped = False
                continue

            if character == "\\":
                escaped = True
                continue

            if character == '"':
                in_string = not in_string
                continue

            if (
                not in_string
                and character == "/"
                and index + 1 < len(line)
                and line[index + 1] == "/"
            ):
                return line[:index]

        return line


def analyze_java_source(
    file_path: str,
    source: str,
) -> list[Issue]:
    analyzer = JavaAnalyzer(
        file_path=file_path,
        source=source,
    )

    return analyzer.analyze()