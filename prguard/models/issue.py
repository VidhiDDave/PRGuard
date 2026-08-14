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


@dataclass(frozen=True)
class Issue:
    rule_id: str
    severity: Severity
    file_path: str
    line: int
    message: str
    suggestion: str | None = None
    category: str = "general"