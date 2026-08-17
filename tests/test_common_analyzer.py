from prguard.analyzers.common import (
    analyze_common_source,
)


def get_rule_ids(
    source: str,
    language: str = "python",
) -> set[str]:
    issues = analyze_common_source(
        "Example.txt",
        source,
        language,
    )

    return {
        issue.rule_id
        for issue in issues
    }


def test_detects_aws_access_key():
    access_key = (
        "AKIA"
        + "ABCDEFGHIJKLMNOP"
    )

    source = (
        f'key = "{access_key}"'
    )

    assert (
        "common-aws-access-key"
        in get_rule_ids(source)
    )


def test_detects_private_key():
    private_key_header = (
        "-----BEGIN "
        + "PRIVATE KEY-----"
    )

    source = private_key_header

    assert (
        "common-private-key"
        in get_rule_ids(source)
    )


def test_detects_hardcoded_api_key():
    secret_value = (
        "real-secret-value-123"
    )

    source = (
        'api_key = "'
        + secret_value
        + '"'
    )

    assert (
        "common-hardcoded-secret"
        in get_rule_ids(source)
    )


def test_placeholder_secret_is_allowed():
    source = """
api_key = "your_api_key_here"
"""

    assert (
        "common-hardcoded-secret"
        not in get_rule_ids(source)
    )


def test_detects_todo():
    marker = (
        "TO"
        + "DO"
    )

    source = (
        f"# {marker}: improve this later"
    )

    assert (
        "common-todo-fixme"
        in get_rule_ids(source)
    )


def test_detects_fixme():
    marker = (
        "FIX"
        + "ME"
    )

    source = (
        f"// {marker}: remove workaround"
    )

    assert (
        "common-todo-fixme"
        in get_rule_ids(
            source,
            "swift",
        )
    )


def test_detects_python_breakpoint():
    source = (
        "break"
        + "point()"
    )

    assert (
        "common-debug-output"
        in get_rule_ids(
            source,
            "python",
        )
    )


def test_detects_swift_debug_print():
    source = """
debugPrint(user)
"""

    assert (
        "common-debug-output"
        in get_rule_ids(
            source,
            "swift",
        )
    )


def test_detects_java_system_out():
    source = """
System.out.println(user);
"""

    assert (
        "common-debug-output"
        in get_rule_ids(
            source,
            "java",
        )
    )


def test_normal_python_print_is_allowed():
    source = """
print("Application started")
"""

    assert (
        "common-debug-output"
        not in get_rule_ids(
            source,
            "python",
        )
    )