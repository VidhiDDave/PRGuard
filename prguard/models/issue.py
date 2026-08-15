from dataclasses import dataclass
from enum import IntEnum


class Severity(IntEnum):
    INFO = 10
    WARNING = 20
    HIGH = 30
    CRITICAL = 40

    @property
    def label(self) -> str:
        return self.name.lower()

    @classmethod
    def from_string(
        cls,
        value: str,
    ) -> "Severity":
        normalized = value.strip().upper()

        try:
            return cls[normalized]

        except KeyError as error:
            raise ValueError(
                f"Unknown severity: {value}"
            ) from error


@dataclass(frozen=True)
class Issue:
    rule_id: str
    severity: Severity
    file_path: str
    line: int
    message: str
    suggestion: str | None = None
    category: str = "general"