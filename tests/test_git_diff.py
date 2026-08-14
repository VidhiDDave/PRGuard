from prguard.git.diff import (
    ChangedFile,
    parse_changed_lines,
)


def test_parse_single_changed_line():
    diff = """
@@ -10 +10 @@
-old
+new
"""

    assert parse_changed_lines(
        diff
    ) == {10}


def test_parse_multiple_changed_lines():
    diff = """
@@ -20,2 +20,4 @@
-old
-old2
+new
+new2
+new3
+new4
"""

    assert parse_changed_lines(
        diff
    ) == {
        20,
        21,
        22,
        23,
    }


def test_parse_multiple_diff_hunks():
    diff = """
@@ -1 +1,2 @@
-old
+new
+new2
@@ -50 +51,3 @@
-old
+one
+two
+three
"""

    assert parse_changed_lines(
        diff
    ) == {
        1,
        2,
        51,
        52,
        53,
    }


def test_changed_file_detects_python():
    changed_file = ChangedFile(
        path="services/api.py",
        changed_lines={
            10,
            11,
        },
    )

    assert (
        changed_file.language
        == "python"
    )


def test_changed_file_detects_swift():
    changed_file = ChangedFile(
        path="ProfileView.swift",
        changed_lines={
            20,
        },
    )

    assert (
        changed_file.language
        == "swift"
    )


def test_changed_file_detects_java():
    changed_file = ChangedFile(
        path="UserService.java",
        changed_lines={
            30,
        },
    )

    assert (
        changed_file.language
        == "java"
    )