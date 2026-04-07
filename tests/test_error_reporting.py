from __future__ import annotations

import json
from pathlib import Path

from engine.errors import LeafMeasureError, write_failure_report


def test_write_failure_report_serializes_machine_readable_payload(tmp_path: Path) -> None:
    error = LeafMeasureError(
        stage="runtime_discovery",
        code="missing_assets",
        message="Could not resolve leaf-measure assets.",
        hints=["Run python -m engine.cli fetch-assets"],
        details={"config_path": Path("D:/tmp/config/runtime.toml")},
    )

    report_path = write_failure_report(tmp_path / "failure.json", error)
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert payload["ok"] is False
    assert payload["stage"] == "runtime_discovery"
    assert payload["code"] == "missing_assets"
    assert "fetch-assets" in payload["hints"][0]
    assert payload["details"]["config_path"].endswith("runtime.toml")
