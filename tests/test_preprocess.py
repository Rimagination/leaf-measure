from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from engine.preprocess import StageInputReport, should_prefer_thumbnail_repair, stage_input_images


def _write_rgb(path: Path, array: np.ndarray) -> None:
    Image.fromarray(array.astype(np.uint8), mode="RGB").save(path)


def test_stage_input_images_whitens_dark_edge_artifacts(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "staged"
    input_dir.mkdir()

    image = np.full((40, 40, 3), 240, dtype=np.uint8)
    image[0:4, :, :] = 0
    image[:, 0:4, :] = 0
    image[16:24, 16:24, :] = np.array([50, 140, 50], dtype=np.uint8)
    source = input_dir / "border.png"
    _write_rgb(source, image)

    report = stage_input_images(input_dir, output_dir)

    staged = np.array(Image.open(output_dir / "border.png").convert("RGB"))
    assert report.modified_files == ["border.png"]
    assert staged[0, 0].tolist() == [255, 255, 255]
    assert staged[20, 20].tolist() == [50, 140, 50]


def test_stage_input_images_leaves_clean_inputs_unchanged(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "staged"
    input_dir.mkdir()

    image = np.full((40, 40, 3), 240, dtype=np.uint8)
    image[16:24, 16:24, :] = np.array([50, 140, 50], dtype=np.uint8)
    source = input_dir / "clean.png"
    _write_rgb(source, image)

    report = stage_input_images(input_dir, output_dir)

    staged = np.array(Image.open(output_dir / "clean.png").convert("RGB"))
    assert report.modified_files == []
    np.testing.assert_array_equal(staged, image)


def test_should_prefer_thumbnail_repair_tracks_dark_edge_preflight() -> None:
    assert should_prefer_thumbnail_repair(
        StageInputReport(staged_dir=Path("staged"), modified_files=["bad_scan.tiff"])
    )
    assert not should_prefer_thumbnail_repair(
        StageInputReport(staged_dir=Path("staged"), modified_files=[])
    )
