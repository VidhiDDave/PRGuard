import re

from prguard.models import Issue, Severity


_FORCE_UNWRAP_PATTERN = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*"
    r"(?:\.[A-Za-z_][A-Za-z0-9_]*)*!"
)

_LOOP_PATTERN = re.compile(
    r"^\s*(for|while)\b"
)

_NETWORK_PATTERNS = (
    "URLSession.shared.dataTask",
    "URLSession.shared.data(",
    ".dataTask(",
    ".uploadTask(",
    ".downloadTask(",
)


class SwiftAnalyzer:
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

            self._check_force_try(
                line_number,
                line,
            )

            self._check_force_cast(
                line_number,
                line,
            )

            self._check_force_unwrap(
                line_number,
                line,
            )

            self._check_unowned_self(
                line_number,
                line,
            )

            self._check_main_queue_sync(
                line_number,
                line,
            )

            self._check_blocking_sleep(
                line_number,
                line,
            )

            self._check_network_call_in_loop(
                line_number,
                line,
            )

            self._check_insecure_url(
                line_number,
                line,
            )

            self._check_fatal_error(
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

    def _check_force_try(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if re.search(
            r"\btry!\s*",
            line,
        ):
            self._add_issue(
                rule_id="swift-force-try",
                severity=Severity.HIGH,
                line=line_number,
                message=(
                    "Forced try will crash if the "
                    "operation throws an error."
                ),
                suggestion=(
                    "Use do/catch, try?, or propagate "
                    "the error instead of try!."
                ),
                category="stability",
            )

    def _check_force_cast(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if re.search(
            r"\bas!\s+",
            line,
        ):
            self._add_issue(
                rule_id="swift-force-cast",
                severity=Severity.HIGH,
                line=line_number,
                message=(
                    "Forced type cast can crash when "
                    "the runtime type does not match."
                ),
                suggestion=(
                    "Prefer `as?` with safe handling "
                    "when the type is not guaranteed."
                ),
                category="stability",
            )

    def _check_force_unwrap(
        self,
        line_number: int,
        line: str,
    ) -> None:
        cleaned = re.sub(
            r"\btry!",
            "",
            line,
        )

        cleaned = re.sub(
            r"\bas!",
            "",
            cleaned,
        )

        cleaned = cleaned.replace(
            "!=",
            "",
        )

        if _FORCE_UNWRAP_PATTERN.search(
            cleaned
        ):
            self._add_issue(
                rule_id="swift-force-unwrap",
                severity=Severity.WARNING,
                line=line_number,
                message=(
                    "Forced optional unwrap may crash "
                    "when the value is nil."
                ),
                suggestion=(
                    "Prefer optional binding, guard, "
                    "nil coalescing, or safe chaining "
                    "when nil is possible."
                ),
                category="stability",
            )

    def _check_unowned_self(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if re.search(
            r"\[\s*unowned\s+self\s*\]",
            line,
        ):
            self._add_issue(
                rule_id="swift-unowned-self",
                severity=Severity.WARNING,
                line=line_number,
                message=(
                    "An unowned self capture assumes "
                    "self will outlive the closure."
                ),
                suggestion=(
                    "Confirm the lifetime guarantee or "
                    "consider `[weak self]` when the "
                    "closure may outlive the object."
                ),
                category="memory",
            )

    def _check_main_queue_sync(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if "DispatchQueue.main.sync" in line:
            self._add_issue(
                rule_id="swift-main-queue-sync",
                severity=Severity.HIGH,
                line=line_number,
                message=(
                    "Synchronous dispatch to the main "
                    "queue can deadlock when called "
                    "from the main thread."
                ),
                suggestion=(
                    "Prefer asynchronous dispatch or "
                    "ensure the code cannot execute "
                    "from the main queue."
                ),
                category="concurrency",
            )

    def _check_blocking_sleep(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if "Thread.sleep" in line:
            self._add_issue(
                rule_id="swift-blocking-sleep",
                severity=Severity.WARNING,
                line=line_number,
                message=(
                    "Thread.sleep blocks the current "
                    "thread."
                ),
                suggestion=(
                    "Prefer asynchronous timing APIs "
                    "or Task.sleep in async code."
                ),
                category="concurrency",
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
            for pattern in _NETWORK_PATTERNS
        ):
            self._add_issue(
                rule_id="swift-network-call-in-loop",
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

    def _check_insecure_url(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if re.search(
            r'URL\s*\(\s*string:\s*"http://',
            line,
        ):
            self._add_issue(
                rule_id="swift-insecure-url",
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

    def _check_fatal_error(
        self,
        line_number: int,
        line: str,
    ) -> None:
        if re.search(
            r"\bfatalError\s*\(",
            line,
        ):
            self._add_issue(
                rule_id="swift-fatal-error",
                severity=Severity.WARNING,
                line=line_number,
                message=(
                    "fatalError terminates the "
                    "application when executed."
                ),
                suggestion=(
                    "Confirm termination is intentional "
                    "and cannot occur during normal "
                    "user flows."
                ),
                category="stability",
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


def analyze_swift_source(
    file_path: str,
    source: str,
) -> list[Issue]:
    analyzer = SwiftAnalyzer(
        file_path=file_path,
        source=source,
    )

    return analyzer.analyze()