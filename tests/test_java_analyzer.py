from prguard.analyzers.java import (
    analyze_java_source,
)


def get_rule_ids(
    source: str,
) -> set[str]:
    issues = analyze_java_source(
        "Example.java",
        source,
    )

    return {
        issue.rule_id
        for issue in issues
    }


def test_detects_empty_catch():
    source = """
try {
    run();
} catch (IOException error) {}
"""

    assert (
        "java-empty-catch"
        in get_rule_ids(source)
    )


def test_detects_broad_exception():
    source = """
try {
    run();
} catch (Exception error) {
    recover();
}
"""

    assert (
        "java-broad-exception"
        in get_rule_ids(source)
    )


def test_detects_system_exit():
    source = """
System.exit(1);
"""

    assert (
        "java-system-exit"
        in get_rule_ids(source)
    )


def test_detects_thread_sleep():
    source = """
Thread.sleep(1000);
"""

    assert (
        "java-thread-sleep"
        in get_rule_ids(source)
    )


def test_detects_runtime_exec():
    source = """
Runtime.getRuntime().exec(command);
"""

    assert (
        "java-runtime-exec"
        in get_rule_ids(source)
    )


def test_detects_insecure_url():
    source = """
URL url = new URL("http://example.com");
"""

    assert (
        "java-insecure-url"
        in get_rule_ids(source)
    )


def test_https_url_is_allowed():
    source = """
URL url = new URL("https://example.com");
"""

    assert (
        "java-insecure-url"
        not in get_rule_ids(source)
    )


def test_detects_network_call_in_loop():
    source = """
for (User user : users) {
    client.send(request);
}
"""

    assert (
        "java-network-call-in-loop"
        in get_rule_ids(source)
    )


def test_network_call_outside_loop_is_allowed():
    source = """
client.send(request);
"""

    assert (
        "java-network-call-in-loop"
        not in get_rule_ids(source)
    )


def test_detects_database_call_in_loop():
    source = """
for (User user : users) {
    statement.executeQuery(sql);
}
"""

    assert (
        "java-database-call-in-loop"
        in get_rule_ids(source)
    )


def test_comment_does_not_trigger_runtime_exec():
    source = """
// Runtime.getRuntime().exec(command);
System.out.println("safe");
"""

    assert (
        "java-runtime-exec"
        not in get_rule_ids(source)
    )


def test_http_inside_string_is_not_comment():
    source = """
URL url = new URL("http://example.com");
"""

    assert (
        "java-insecure-url"
        in get_rule_ids(source)
    )