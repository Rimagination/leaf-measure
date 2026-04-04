from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_doctor_writes_machine_readable_report(
    repo_root: Path,
    local_fiji_dir: Path,
    available_assets_dir: Path,
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "doctor.json"
    cmd = [
        sys.executable,
        "-m",
        "engine.cli",
        "doctor",
        "--fiji",
        str(local_fiji_dir),
        "--assets",
        str(available_assets_dir),
        "--output",
        str(report_path),
    ]
    result = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["fiji_dir"].endswith("Fiji")
    assert payload["assets_dir"]


def test_analyze_missing_assets_writes_failure_report(
    repo_root: Path,
    local_fiji_dir: Path,
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "sample.png").write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\xd9\x8f\x18\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    output_dir = tmp_path / "run"
    missing_assets = tmp_path / "missing-assets"
    cmd = [
        sys.executable,
        "-m",
        "engine.cli",
        "analyze",
        "--input",
        str(input_dir),
        "--output",
        str(output_dir),
        "--mode",
        "full",
        "--fiji",
        str(local_fiji_dir),
        "--assets",
        str(missing_assets),
    ]
    result = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)

    assert result.returncode == 2
    failure_path = output_dir / "failure.json"
    assert failure_path.exists()
    payload = json.loads(failure_path.read_text(encoding="utf-8"))
    assert payload["code"] in {"file_not_found", "analysis_failed"}
