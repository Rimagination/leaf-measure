from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from engine.full_mask_polarity import (
    analyze_full_measurement_mask_polarity,
    select_full_measurement_inversion_files,
)


def _save_mask(path: Path, array: np.ndarray) -> None:
    Image.fromarray(array.astype(np.uint8), mode="L").save(path)


def test_analyze_full_measurement_mask_polarity_detects_hole_dominated_case(tmp_path: Path) -> None:
    image = np.zeros((140, 140), dtype=np.uint8)
    image[0, :] = 255
    image[-1, :] = 255
    image[:, 0] = 255
    image[:, -1] = 255

    leaves = [
        (15, 15, 45, 55),
        (55, 20, 95, 60),
        (95, 25, 125, 65),
    ]
    for y0, x0, y1, x1 in leaves:
        image[y0:y1, x0:x1] = 255
        image[y0 + 8 : y1 - 8, x0 + 8 : x1 - 8] = 0

    path = tmp_path / "compound_mask.png"
    _save_mask(path, image)

    decision = analyze_full_measurement_mask_polarity(path, min_area=20)

    assert decision.should_invert
    assert decision.current_component_count > decision.inverted_component_count
    assert decision.current_largest_component_area_ratio >= 0.5


def test_analyze_full_measurement_mask_polarity_keeps_reasonable_black_foreground_mask(tmp_path: Path) -> None:
    image = np.full((120, 120), 255, dtype=np.uint8)
    image[15:105, 20:90] = 0
    image[40:80, 95:110] = 0

    path = tmp_path / "simple_leaf_mask.png"
    _save_mask(path, image)

    decision = analyze_full_measurement_mask_polarity(path, min_area=20)

    assert not decision.should_invert
    assert decision.current_component_count == 2


def test_analyze_full_measurement_mask_polarity_detects_single_hole_dominated_case_with_source_image(
    tmp_path: Path,
) -> None:
    mask = np.full((240, 180), 255, dtype=np.uint8)
    mask[10:230, 10:170] = 0
    mask[105:155, 80:115] = 255

    source = np.full((240, 180), 240, dtype=np.uint8)
    source[105:155, 80:115] = 90

    path = tmp_path / "single_hole_mask.png"
    source_path = tmp_path / "single_hole_source.png"
    _save_mask(path, mask)
    _save_mask(source_path, source)

    decision = analyze_full_measurement_mask_polarity(path, min_area=20, source_path=source_path)

    assert decision.should_invert
    assert decision.current_component_count == 1
    assert decision.inverted_component_count == 1
    assert decision.current_largest_component_area_ratio > 0.5
    assert decision.inverted_largest_component_area_ratio < 0.05
    assert decision.current_source_score is not None
    assert decision.inverted_source_score is not None
    assert decision.inverted_source_score > decision.current_source_score


def test_analyze_full_measurement_mask_polarity_keeps_single_large_leaf_with_source_image(tmp_path: Path) -> None:
    mask = np.full((240, 180), 255, dtype=np.uint8)
    mask[20:220, 40:140] = 0

    source = np.full((240, 180), 240, dtype=np.uint8)
    source[20:220, 40:140] = 90

    path = tmp_path / "single_large_leaf.png"
    source_path = tmp_path / "single_large_leaf_source.png"
    _save_mask(path, mask)
    _save_mask(source_path, source)

    decision = analyze_full_measurement_mask_polarity(path, min_area=20, source_path=source_path)

    assert not decision.should_invert
    assert decision.current_component_count == 1
    assert decision.inverted_component_count == 0


def test_select_full_measurement_inversion_files_returns_only_detected_masks(tmp_path: Path) -> None:
    area_dir = tmp_path / "area"
    source_dir = tmp_path / "input"
    area_dir.mkdir()
    source_dir.mkdir()

    invert_me = np.zeros((100, 100), dtype=np.uint8)
    invert_me[[0, -1], :] = 255
    invert_me[:, [0, -1]] = 255
    invert_me[15:40, 15:45] = 255
    invert_me[20:35, 20:40] = 0
    invert_me[55:85, 55:90] = 255
    invert_me[62:78, 62:83] = 0
    keep_me = np.full((100, 100), 255, dtype=np.uint8)
    keep_me[20:70, 25:65] = 0

    invert_path = area_dir / "invert.png"
    keep_path = area_dir / "keep.png"
    _save_mask(invert_path, invert_me)
    _save_mask(keep_path, keep_me)
    source_invert = np.full((100, 100), 240, dtype=np.uint8)
    source_invert[15:40, 15:45] = 100
    source_invert[55:85, 55:90] = 100
    source_keep = np.full((100, 100), 240, dtype=np.uint8)
    source_keep[20:70, 25:65] = 100
    _save_mask(source_dir / "invert.png", source_invert)
    _save_mask(source_dir / "keep.png", source_keep)

    report = select_full_measurement_inversion_files(area_dir, min_area=20, source_image_dir=source_dir)

    assert report.invert_files == ["invert.png"]
    inverted_pixels = np.array(Image.open(invert_path).convert("L"))
    kept_pixels = np.array(Image.open(keep_path).convert("L"))
    assert inverted_pixels[0, 0] == 255
    assert kept_pixels[0, 0] == 255
