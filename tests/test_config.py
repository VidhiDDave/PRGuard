import pytest

from prguard.config import (
    ConfigError,
    ReviewConfig,
    load_config,
)
from prguard.models import Severity


def test_missing_config_uses_defaults(
    tmp_path,
):
    config = load_config(
        tmp_path / "missing.toml"
    )

    assert (
        config.fail_on
        == Severity.HIGH
    )

    assert (
        config.enabled_languages
        == frozenset(
            {
                "python",
                "swift",
                "java",
            }
        )
    )

    assert (
        config.disabled_rules
        == frozenset()
    )

    assert (
        config.ignored_paths
        == ()
    )


def test_loads_review_settings(
    tmp_path,
):
    config_path = (
        tmp_path
        / ".prguard.toml"
    )

    config_path.write_text(
        """
[review]
fail_on = "warning"
disabled_rules = [
    "common-todo-fixme",
]
ignored_paths = [
    "generated/**",
]
""",
        encoding="utf-8",
    )

    config = load_config(
        config_path
    )

    assert (
        config.fail_on
        == Severity.WARNING
    )

    assert (
        "common-todo-fixme"
        in config.disabled_rules
    )

    assert (
        config.ignored_paths
        == (
            "generated/**",
        )
    )


def test_language_can_be_disabled(
    tmp_path,
):
    config_path = (
        tmp_path
        / ".prguard.toml"
    )

    config_path.write_text(
        """
[languages]
python = true
swift = false
java = true
""",
        encoding="utf-8",
    )

    config = load_config(
        config_path
    )

    assert (
        config.is_language_enabled(
            "python"
        )
        is True
    )

    assert (
        config.is_language_enabled(
            "swift"
        )
        is False
    )


def test_ignored_path_matches_glob():
    config = ReviewConfig(
        ignored_paths=(
            "generated/**",
        )
    )

    assert (
        config.is_path_ignored(
            "generated/models/User.py"
        )
        is True
    )

    assert (
        config.is_path_ignored(
            "src/User.py"
        )
        is False
    )


def test_disabled_rule_is_not_enabled():
    config = ReviewConfig(
        disabled_rules=frozenset(
            {
                "common-todo-fixme",
            }
        )
    )

    assert (
        config.is_rule_enabled(
            "common-todo-fixme"
        )
        is False
    )

    assert (
        config.is_rule_enabled(
            "python-mutable-default"
        )
        is True
    )


def test_invalid_fail_on_raises_error(
    tmp_path,
):
    config_path = (
        tmp_path
        / ".prguard.toml"
    )

    config_path.write_text(
        """
[review]
fail_on = "dangerous"
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigError
    ):
        load_config(
            config_path
        )


def test_unknown_language_raises_error(
    tmp_path,
):
    config_path = (
        tmp_path
        / ".prguard.toml"
    )

    config_path.write_text(
        """
[languages]
ruby = true
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigError
    ):
        load_config(
            config_path
        )


def test_language_value_must_be_boolean(
    tmp_path,
):
    config_path = (
        tmp_path
        / ".prguard.toml"
    )

    config_path.write_text(
        """
[languages]
swift = "yes"
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigError
    ):
        load_config(
            config_path
        )


def test_disabled_rules_must_be_list(
    tmp_path,
):
    config_path = (
        tmp_path
        / ".prguard.toml"
    )

    config_path.write_text(
        """
[review]
disabled_rules = "rule-name"
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigError
    ):
        load_config(
            config_path
        )


def test_invalid_toml_raises_error(
    tmp_path,
):
    config_path = (
        tmp_path
        / ".prguard.toml"
    )

    config_path.write_text(
        """
[review
fail_on = "high"
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigError
    ):
        load_config(
            config_path
        )