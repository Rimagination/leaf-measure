from __future__ import annotations

import json
from pathlib import Path


def test_thumbnails_mode_produces_outputs(
    repo_root: Path,
    local_fiji_dir: Path,
    available_assets_dir: Path,
    tmp_path: Path,
) -> None:
    from conftest import normalized_csv_rows, run_cli

    input_dir = available_assets_dir / "fixtures" / "trial_input"
    output_dir = tmp_path / "thumbs-run"
    result = run_cli(
        repo_root=repo_root,
        input_dir=input_dir,
        output_dir=output_dir,
        mode="thumbnails",
        fiji_dir=local_fiji_dir,
        assets_dir=available_assets_dir,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert (output_dir / "results.csv").exists()
    assert any((output_dir / "02_thumbnails").glob("*"))
    assert any((output_dir / "03_area").glob("*"))
    assert any((output_dir / "04_outline").glob("*"))
    assert len(normalized_csv_rows(output_dir / "results.csv")) > 0

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["mode"] == "thumbnails"
    assert manifest["executor"] == "direct-fiji-batch"
