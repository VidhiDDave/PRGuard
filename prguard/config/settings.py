import tomllib
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from prguard.models import Severity


DEFAULT_CONFIG_PATH = ".prguard.toml"

SUPPORTED_LANGUAGES = frozenset(
    {
        "python",
        "swift",
        "java",
    }
)


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class AIConfig:
    enabled: bool = False
    model: str = "gpt-5.5"
    max_changed_lines: int = 400


@dataclass(frozen=True)
class ReviewConfig:
    fail_on: Severity = Severity.HIGH
    enabled_languages: frozenset[str] = (
        SUPPORTED_LANGUAGES
    )
    disabled_rules: frozenset[str] = (
        frozenset()
    )
    ignored_paths: tuple[str, ...] = ()
    ai: AIConfig = AIConfig()

    def is_language_enabled(
        self,
        language: str,
    ) -> bool:
        return (
            language
            in self.enabled_languages
        )

    def is_rule_enabled(
        self,
        rule_id: str,
    ) -> bool:
        return (
            rule_id
            not in self.disabled_rules
        )

    def is_path_ignored(
        self,
        file_path: str,
    ) -> bool:
        normalized_path = (
            file_path.replace(
                "\\",
                "/",
            )
        )

        for pattern in self.ignored_paths:
            normalized_pattern = (
                pattern.replace(
                    "\\",
                    "/",
                )
            )

            if fnmatch(
                normalized_path,
                normalized_pattern,
            ):
                return True

            if (
                normalized_pattern.endswith("/")
                and normalized_path.startswith(
                    normalized_pattern
                )
            ):
                return True

        return False


def _get_table(
    data: dict,
    name: str,
) -> dict:
    value = data.get(
        name,
        {},
    )

    if not isinstance(
        value,
        dict,
    ):
        raise ConfigError(
            f"Configuration section "
            f"'{name}' must be a table."
        )

    return value


def _parse_string_list(
    value,
    field_name: str,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if not isinstance(
        value,
        list,
    ):
        raise ConfigError(
            f"Configuration field "
            f"'{field_name}' must be a list."
        )

    result: list[str] = []

    for item in value:
        if (
            not isinstance(
                item,
                str,
            )
            or not item.strip()
        ):
            raise ConfigError(
                f"Every value in "
                f"'{field_name}' must be "
                "a non-empty string."
            )

        result.append(
            item.strip()
        )

    return tuple(
        result
    )


def _parse_fail_on(
    review_table: dict,
) -> Severity:
    raw_value = review_table.get(
        "fail_on",
        "high",
    )

    if not isinstance(
        raw_value,
        str,
    ):
        raise ConfigError(
            "'review.fail_on' must "
            "be a severity string."
        )

    try:
        return Severity.from_string(
            raw_value
        )

    except ValueError as error:
        raise ConfigError(
            "'review.fail_on' must be "
            "one of: info, warning, "
            "high, critical."
        ) from error


def _parse_languages(
    languages_table: dict,
) -> frozenset[str]:
    unknown_languages = (
        set(languages_table)
        - SUPPORTED_LANGUAGES
    )

    if unknown_languages:
        names = ", ".join(
            sorted(
                unknown_languages
            )
        )

        raise ConfigError(
            f"Unsupported language "
            f"configuration: {names}."
        )

    enabled_languages: set[str] = set()

    for language in SUPPORTED_LANGUAGES:
        enabled = languages_table.get(
            language,
            True,
        )

        if not isinstance(
            enabled,
            bool,
        ):
            raise ConfigError(
                f"'languages.{language}' "
                "must be true or false."
            )

        if enabled:
            enabled_languages.add(
                language
            )

    return frozenset(
        enabled_languages
    )


def _parse_ai(
    ai_table: dict,
) -> AIConfig:
    enabled = ai_table.get(
        "enabled",
        False,
    )

    if not isinstance(
        enabled,
        bool,
    ):
        raise ConfigError(
            "'ai.enabled' must be "
            "true or false."
        )

    model = ai_table.get(
        "model",
        "gpt-5.5",
    )

    if (
        not isinstance(
            model,
            str,
        )
        or not model.strip()
    ):
        raise ConfigError(
            "'ai.model' must be a "
            "non-empty string."
        )

    max_changed_lines = ai_table.get(
        "max_changed_lines",
        400,
    )

    if (
        not isinstance(
            max_changed_lines,
            int,
        )
        or isinstance(
            max_changed_lines,
            bool,
        )
        or max_changed_lines <= 0
    ):
        raise ConfigError(
            "'ai.max_changed_lines' "
            "must be a positive integer."
        )

    return AIConfig(
        enabled=enabled,
        model=model.strip(),
        max_changed_lines=max_changed_lines,
    )


def load_config(
    path: str | Path = DEFAULT_CONFIG_PATH,
) -> ReviewConfig:
    config_path = Path(
        path
    )

    if not config_path.exists():
        return ReviewConfig()

    try:
        with config_path.open(
            "rb"
        ) as file:
            data = tomllib.load(
                file
            )

    except tomllib.TOMLDecodeError as error:
        raise ConfigError(
            f"Invalid TOML in "
            f"{config_path}: {error}"
        ) from error

    except OSError as error:
        raise ConfigError(
            f"Could not read "
            f"{config_path}: {error}"
        ) from error

    review_table = _get_table(
        data,
        "review",
    )

    languages_table = _get_table(
        data,
        "languages",
    )

    ai_table = _get_table(
        data,
        "ai",
    )

    fail_on = _parse_fail_on(
        review_table
    )

    disabled_rules = frozenset(
        _parse_string_list(
            review_table.get(
                "disabled_rules"
            ),
            "review.disabled_rules",
        )
    )

    ignored_paths = _parse_string_list(
        review_table.get(
            "ignored_paths"
        ),
        "review.ignored_paths",
    )

    enabled_languages = (
        _parse_languages(
            languages_table
        )
    )

    ai = _parse_ai(
        ai_table
    )

    return ReviewConfig(
        fail_on=fail_on,
        enabled_languages=(
            enabled_languages
        ),
        disabled_rules=(
            disabled_rules
        ),
        ignored_paths=(
            ignored_paths
        ),
        ai=ai,
    )