from prguard.analyzers.swift import (
    analyze_swift_source,
)


def get_rule_ids(
    source: str,
) -> set[str]:
    issues = analyze_swift_source(
        "Example.swift",
        source,
    )

    return {
        issue.rule_id
        for issue in issues
    }


def test_detects_force_try():
    source = """
let value = try! loadValue()
"""

    assert (
        "swift-force-try"
        in get_rule_ids(source)
    )


def test_detects_force_cast():
    source = """
let user = value as! User
"""

    assert (
        "swift-force-cast"
        in get_rule_ids(source)
    )


def test_detects_force_unwrap():
    source = """
let name = user.name!
"""

    assert (
        "swift-force-unwrap"
        in get_rule_ids(source)
    )


def test_optional_comparison_is_not_force_unwrap():
    source = """
if user != nil {
    print("user exists")
}
"""

    assert (
        "swift-force-unwrap"
        not in get_rule_ids(source)
    )


def test_detects_unowned_self():
    source = """
service.load { [unowned self] in
    self.update()
}
"""

    assert (
        "swift-unowned-self"
        in get_rule_ids(source)
    )


def test_weak_self_is_allowed():
    source = """
service.load { [weak self] in
    self?.update()
}
"""

    assert (
        "swift-unowned-self"
        not in get_rule_ids(source)
    )


def test_detects_main_queue_sync():
    source = """
DispatchQueue.main.sync {
    updateUI()
}
"""

    assert (
        "swift-main-queue-sync"
        in get_rule_ids(source)
    )


def test_detects_thread_sleep():
    source = """
Thread.sleep(forTimeInterval: 1)
"""

    assert (
        "swift-blocking-sleep"
        in get_rule_ids(source)
    )


def test_detects_network_call_in_for_loop():
    source = """
for user in users {
    URLSession.shared.dataTask(
        with: user.url
    )
}
"""

    assert (
        "swift-network-call-in-loop"
        in get_rule_ids(source)
    )


def test_network_call_outside_loop_is_allowed():
    source = """
URLSession.shared.dataTask(
    with: url
)
"""

    assert (
        "swift-network-call-in-loop"
        not in get_rule_ids(source)
    )


def test_detects_network_call_in_while_loop():
    source = """
while shouldContinue {
    URLSession.shared.dataTask(
        with: url
    )
}
"""

    assert (
        "swift-network-call-in-loop"
        in get_rule_ids(source)
    )


def test_detects_insecure_http_url():
    source = """
let url = URL(string: "http://example.com")
"""

    assert (
        "swift-insecure-url"
        in get_rule_ids(source)
    )


def test_https_url_is_allowed():
    source = """
let url = URL(string: "https://example.com")
"""

    assert (
        "swift-insecure-url"
        not in get_rule_ids(source)
    )


def test_detects_fatal_error():
    source = """
fatalError("Unexpected state")
"""

    assert (
        "swift-fatal-error"
        in get_rule_ids(source)
    )


def test_comment_does_not_trigger_force_try():
    source = """
// let value = try! loadValue()
let value = try? loadValue()
"""

    assert (
        "swift-force-try"
        not in get_rule_ids(source)
    )