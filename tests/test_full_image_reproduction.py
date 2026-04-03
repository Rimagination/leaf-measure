from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_full_image_reproduces_bundled_golden(
    repo_root: Path,
    local_fiji_dir: Path,
    validation_assets_dir: Path,
    tmp_path: Path,
) -> None:
    from conftest import run_cli, sha256

    input_dir = validation_assets_dir / "fixtures" / "trial_input"
    output_dir = tmp_path / "full-run"
    result = run_cli(
        repo_root=repo_root,
        input_dir=input_dir,
        output_dir=output_dir,
        mode="full",
        fiji_dir=local_fiji_dir,
        assets_dir=validation_assets_dir,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert (output_dir / "results.csv").exists()
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "run_summary.md").exists()
    assert (output_dir / "method_summary.md").exists()
    assert (output_dir / "trait_explanations.md").exists()

    produced = pd.read_csv(output_dir / "results.csv")
    golden = pd.read_csv(validation_assets_dir / "golden" / "full_image" / "results_full.csv")
    for frame in (produced, golden):
        drop_columns = [column for column in frame.columns if str(column).startswith("Unnamed:") or not str(column).strip()]
        if drop_columns:
            frame.drop(columns=drop_columns, inplace=True)
        for column in ["Area", "Perim.", "Circ.", "Length", "Width ", "Solidity"]:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
    assert list(produced["Label"]) == list(golden["Label"])
    pd.testing.assert_frame_equal(produced, golden, check_exact=False, atol=1e-6, rtol=0)

    for folder in ["02_area", "03_outline"]:
        produced_files = sorted((output_dir / folder).glob("*.png"))
        golden_files = sorted((validation_assets_dir / "golden" / "full_image" / folder).glob("*.png"))
        assert [file.name for file in produced_files] == [file.name for file in golden_files]
        assert [sha256(file) for file in produced_files] == [sha256(file) for file in golden_files]

    manifest = (output_dir / "manifest.json").read_text(encoding="utf-8")
    assert '"mode": "full"' in manifest
    assert '"executor": "direct-fiji-batch"' in manifest
