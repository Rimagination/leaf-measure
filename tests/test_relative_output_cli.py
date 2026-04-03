from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys


def test_cli_supports_relative_output_paths(
    repo_root: Path,
    local_fiji_dir: Path,
    available_assets_dir: Path,
) -> None:
    output_dir = repo_root / "_relative_cli_run"
    if output_dir.exists():
        shutil.rmtree(output_dir)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "engine.cli",
            "analyze",
            "--input",
            str(available_assets_dir / "fixtures" / "trial_input"),
            "--output",
            "_relative_cli_run",
            "--mode",
            "full",
            "--fiji",
            str(local_fiji_dir),
            "--assets",
            str(available_assets_dir),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )

    try:
        assert result.returncode == 0, result.stderr or result.stdout
        assert (output_dir / "results.csv").exists()
        assert (output_dir / "_work" / "run.ijm").exists()
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)
