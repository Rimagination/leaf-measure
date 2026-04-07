from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


@dataclass
class LeafMeasureError(Exception):
    code: str
    message: str
    stage: str = "analysis_execution"
    hints: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def payload(self) -> dict[str, Any]:
        def convert(value: Any):
            if isinstance(value, Path):
                return str(value)
            if isinstance(value, list):
                return [convert(item) for item in value]
            if isinstance(value, tuple):
                return list(value)
            if isinstance(value, dict):
                return {key: convert(item) for key, item in value.items()}
            return value

        return {
            "ok": False,
            "stage": self.stage,
            "code": self.code,
            "message": self.message,
            "hints": self.hints,
            "details": {key: convert(value) for key, value in self.details.items()},
        }


def write_failure_report(path: Path, error: LeafMeasureError) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(error.payload(), indent=2), encoding="utf-8")
    return path
