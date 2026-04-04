from __future__ import annotations

import json
from pathlib import Path


def test_thumbnails_mode_produces_outputs(
    repo_root: Path,
    local_fiji_dir: Path,
    validation_assets_dir: Path,
    tmp_path: Path,
) -> None:
    from conftest import normalized_csv_rows, run_cli, sha256

    input_dir = validation_assets_dir / "fixtures" / "trial_input"
    output_dir = tmp_path / "thumbs-run"
    result = run_cli(
        repo_root=repo_root,
        input_dir=input_dir,
        output_dir=output_dir,
        mode="thumbnails",
        fiji_dir=local_fiji_dir,
        assets_dir=validation_assets_dir,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert (output_dir / "results.csv").exists()
    assert (output_dir / "results_fameles_particles_raw.csv").exists()
    assert any((output_dir / "02_thumbnails").glob("*"))
    assert any((output_dir / "03_area").glob("*"))
    assert any((output_dir / "04_outline").glob("*"))
    rows = normalized_csv_rows(output_dir / "results.csv")
    assert len(rows) == 13
    raw_rows = normalized_csv_rows(output_dir / "results_fameles_particles_raw.csv")
    assert len(raw_rows) == 25

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["mode"] == "thumbnails"
    assert manifest["executor"] == "direct-fiji-batch"
    assert manifest["corrected_mask_files"] == []
    assert manifest["raw_results_csv"].endswith("results_fameles_particles_raw.csv")

    expected_folders = {
        "02_thumbnails": validation_assets_dir / "golden" / "thumbnails" / "02_thumbnails",
        "03_area": validation_assets_dir / "golden" / "thumbnails" / "03_area",
        "04_outline": validation_assets_dir / "golden" / "thumbnails" / "04_perimeter",
    }
    for produced_name, golden_dir in expected_folders.items():
        produced_files = sorted((output_dir / produced_name).iterdir())
        golden_files = sorted(golden_dir.iterdir())
        assert [file.name for file in produced_files] == [file.name for file in golden_files]
        assert [sha256(file) for file in produced_files] == [sha256(file) for file in golden_files]
