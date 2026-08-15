import ast

from prguard.models import Issue, Severity


class PythonAnalyzer(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.issues: list[Issue] = []

        self.loop_depth = 0
        self.async_depth = 0

        self.context_managed_open_lines: set[int] = set()

    def _add_issue(
        self,
        rule_id: str,
        severity: Severity,
        node: ast.AST,
        message: str,
        suggestion: str,
        category: str,
    ) -> None:
        self.issues.append(
            Issue(
                rule_id=rule_id,
                severity=severity,
                file_path=self.file_path,
                line=getattr(node, "lineno", 1),
                message=message,
                suggestion=suggestion,
                category=category,
            )
        )

    def visit_FunctionDef(
        self,
        node: ast.FunctionDef,
    ) -> None:
        self._check_mutable_defaults(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> None:
        self._check_mutable_defaults(node)

        self.async_depth += 1
        self.generic_visit(node)
        self.async_depth -= 1

    def _check_mutable_defaults(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        defaults = list(node.args.defaults)

        defaults.extend(
            default
            for default in node.args.kw_defaults
            if default is not None
        )

        for default in defaults:
            if isinstance(
                default,
                (
                    ast.List,
                    ast.Dict,
                    ast.Set,
                ),
            ):
                self._add_issue(
                    rule_id="python-mutable-default",
                    severity=Severity.HIGH,
                    node=default,
                    message=(
                        "Mutable default argument can retain "
                        "state between function calls."
                    ),
                    suggestion=(
                        "Use None as the default and create "
                        "the collection inside the function."
                    ),
                    category="correctness",
                )

    def visit_ExceptHandler(
        self,
        node: ast.ExceptHandler,
    ) -> None:
        if node.type is None:
            self._add_issue(
                rule_id="python-bare-except",
                severity=Severity.HIGH,
                node=node,
                message=(
                    "Bare except catches every exception, "
                    "including system-exiting exceptions."
                ),
                suggestion=(
                    "Catch only the specific exception "
                    "types this code expects."
                ),
                category="stability",
            )

        elif (
            isinstance(node.type, ast.Name)
            and node.type.id == "Exception"
        ):
            self._add_issue(
                rule_id="python-broad-except",
                severity=Severity.WARNING,
                node=node,
                message=(
                    "Broad Exception handler may hide "
                    "unexpected failures."
                ),
                suggestion=(
                    "Catch narrower exception types "
                    "when possible."
                ),
                category="stability",
            )

        if (
            len(node.body) == 1
            and isinstance(
                node.body[0],
                ast.Pass,
            )
        ):
            self._add_issue(
                rule_id="python-swallowed-exception",
                severity=Severity.HIGH,
                node=node,
                message="Exception is silently ignored.",
                suggestion=(
                    "Handle, propagate, or intentionally "
                    "log the failure."
                ),
                category="stability",
            )

        self.generic_visit(node)

    def visit_For(
        self,
        node: ast.For,
    ) -> None:
        self.loop_depth += 1
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_AsyncFor(
        self,
        node: ast.AsyncFor,
    ) -> None:
        self.loop_depth += 1
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_While(
        self,
        node: ast.While,
    ) -> None:
        self.loop_depth += 1
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_Call(
        self,
        node: ast.Call,
    ) -> None:
        root, method = self._get_call_parts(node)

        if (
            root is None
            and method in {
                "eval",
                "exec",
            }
        ):
            self._add_issue(
                rule_id="python-dynamic-execution",
                severity=Severity.CRITICAL,
                node=node,
                message=(
                    f"{method}() executes dynamic code."
                ),
                suggestion=(
                    "Avoid dynamic code execution, "
                    "especially with external input."
                ),
                category="security",
            )

        if (
            root == "os"
            and method == "system"
        ):
            self._add_issue(
                rule_id="python-os-system",
                severity=Severity.HIGH,
                node=node,
                message=(
                    "os.system() invokes a shell."
                ),
                suggestion=(
                    "Prefer subprocess with an argument "
                    "list and shell=False."
                ),
                category="security",
            )

        if root == "subprocess":
            self._check_subprocess(node)

        if (
            root == "requests"
            and method
            in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "request",
            }
        ):
            self._check_network_request(node)

        if (
            self.loop_depth > 0
            and method
            in {
                "execute",
                "query",
            }
        ):
            self._add_issue(
                rule_id="python-database-call-in-loop",
                severity=Severity.HIGH,
                node=node,
                message=(
                    "Database operation occurs inside "
                    "a loop."
                ),
                suggestion=(
                    "Consider batching the operation "
                    "to avoid N+1 query behavior."
                ),
                category="performance",
            )

        if (
            self.async_depth > 0
            and root == "time"
            and method == "sleep"
        ):
            self._add_issue(
                rule_id="python-blocking-sleep-in-async",
                severity=Severity.HIGH,
                node=node,
                message=(
                    "time.sleep() blocks the event loop "
                    "inside an async function."
                ),
                suggestion=(
                    "Use await asyncio.sleep(...) instead."
                ),
                category="concurrency",
            )

        if (
            root is None
            and method == "open"
            and node.lineno
            not in self.context_managed_open_lines
        ):
            self._add_issue(
                rule_id="python-open-without-context",
                severity=Severity.WARNING,
                node=node,
                message=(
                    "File is opened outside a context "
                    "manager."
                ),
                suggestion=(
                    "Use `with open(...) as file:` so "
                    "the resource is reliably closed."
                ),
                category="resources",
            )

        self.generic_visit(node)

    def _check_subprocess(
        self,
        node: ast.Call,
    ) -> None:
        shell_true = any(
            keyword.arg == "shell"
            and isinstance(
                keyword.value,
                ast.Constant,
            )
            and keyword.value.value is True
            for keyword in node.keywords
        )

        if shell_true:
            self._add_issue(
                rule_id="python-subprocess-shell",
                severity=Severity.HIGH,
                node=node,
                message=(
                    "subprocess is called with shell=True."
                ),
                suggestion=(
                    "Prefer an argument list with "
                    "shell=False."
                ),
                category="security",
            )

    def _check_network_request(
        self,
        node: ast.Call,
    ) -> None:
        has_timeout = any(
            keyword.arg == "timeout"
            for keyword in node.keywords
        )

        if not has_timeout:
            self._add_issue(
                rule_id="python-request-without-timeout",
                severity=Severity.WARNING,
                node=node,
                message=(
                    "HTTP request does not specify "
                    "a timeout."
                ),
                suggestion=(
                    "Provide a bounded timeout so a "
                    "network request cannot hang indefinitely."
                ),
                category="networking",
            )

        if self.loop_depth > 0:
            self._add_issue(
                rule_id="python-network-call-in-loop",
                severity=Severity.HIGH,
                node=node,
                message=(
                    "Network request occurs inside a loop."
                ),
                suggestion=(
                    "Consider batching, caching, "
                    "deduplication, or bounded concurrency."
                ),
                category="performance",
            )

    @staticmethod
    def _get_call_parts(
        node: ast.Call,
    ) -> tuple[str | None, str | None]:
        function = node.func

        if isinstance(
            function,
            ast.Name,
        ):
            return None, function.id

        if isinstance(
            function,
            ast.Attribute,
        ):
            if isinstance(
                function.value,
                ast.Name,
            ):
                return (
                    function.value.id,
                    function.attr,
                )

        return None, None


def _collect_context_managed_opens(
    tree: ast.AST,
) -> set[int]:
    lines: set[int] = set()

    for node in ast.walk(tree):
        if not isinstance(
            node,
            (
                ast.With,
                ast.AsyncWith,
            ),
        ):
            continue

        for item in node.items:
            expression = item.context_expr

            if not isinstance(
                expression,
                ast.Call,
            ):
                continue

            if (
                isinstance(
                    expression.func,
                    ast.Name,
                )
                and expression.func.id == "open"
            ):
                lines.add(expression.lineno)

    return lines


def analyze_python_source(
    file_path: str,
    source: str,
) -> list[Issue]:
    try:
        tree = ast.parse(
            source,
            filename=file_path,
        )

    except SyntaxError as error:
        return [
            Issue(
                rule_id="python-syntax-error",
                severity=Severity.CRITICAL,
                file_path=file_path,
                line=error.lineno or 1,
                message=(
                    f"Python syntax error: "
                    f"{error.msg}."
                ),
                suggestion=(
                    "Fix the syntax error before merge."
                ),
                category="correctness",
            )
        ]

    analyzer = PythonAnalyzer(
        file_path
    )

    analyzer.context_managed_open_lines = (
        _collect_context_managed_opens(
            tree
        )
    )

    analyzer.visit(tree)

    return analyzer.issues