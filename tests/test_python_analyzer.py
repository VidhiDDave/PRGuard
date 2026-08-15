from prguard.analyzers.python import (
    analyze_python_source,
)


def get_rule_ids(
    source: str,
) -> set[str]:
    issues = analyze_python_source(
        "example.py",
        source,
    )

    return {
        issue.rule_id
        for issue in issues
    }


def test_detects_mutable_default():
    source = """
def add_user(users=[]):
    users.append("test")
"""

    assert (
        "python-mutable-default"
        in get_rule_ids(source)
    )


def test_detects_bare_except():
    source = """
try:
    do_something()
except:
    pass
"""

    rules = get_rule_ids(
        source
    )

    assert (
        "python-bare-except"
        in rules
    )

    assert (
        "python-swallowed-exception"
        in rules
    )


def test_detects_broad_exception():
    source = """
try:
    do_something()
except Exception:
    recover()
"""

    assert (
        "python-broad-except"
        in get_rule_ids(source)
    )


def test_detects_network_call_in_loop():
    source = """
import requests

for user in users:
    requests.get(
        user.url
    )
"""

    rules = get_rule_ids(
        source
    )

    assert (
        "python-network-call-in-loop"
        in rules
    )

    assert (
        "python-request-without-timeout"
        in rules
    )


def test_request_with_timeout_is_allowed():
    source = """
import requests

requests.get(
    "https://example.com",
    timeout=10,
)
"""

    assert (
        "python-request-without-timeout"
        not in get_rule_ids(source)
    )


def test_detects_blocking_sleep_in_async():
    source = """
import time

async def run():
    time.sleep(1)
"""

    assert (
        "python-blocking-sleep-in-async"
        in get_rule_ids(source)
    )


def test_detects_shell_true():
    source = """
import subprocess

subprocess.run(
    command,
    shell=True,
)
"""

    assert (
        "python-subprocess-shell"
        in get_rule_ids(source)
    )


def test_detects_open_without_context_manager():
    source = """
file = open("data.txt")
"""

    assert (
        "python-open-without-context"
        in get_rule_ids(source)
    )


def test_allows_context_managed_open():
    source = """
with open("data.txt") as file:
    contents = file.read()
"""

    assert (
        "python-open-without-context"
        not in get_rule_ids(source)
    )


def test_detects_syntax_error():
    source = """
def broken(
    print("hello")
"""

    assert (
        "python-syntax-error"
        in get_rule_ids(source)
    )


def test_detects_eval():
    source = """
result = eval(user_input)
"""

    assert (
        "python-dynamic-execution"
        in get_rule_ids(source)
    )