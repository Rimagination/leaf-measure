from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from engine.thumbnail_extraction import extract_thumbnails_from_masks


def test_extract_thumbnails_from_masks_exports_one_crop_per_component(tmp_path: Path) -> None:
    mask_dir = tmp_path / "masks"
    image_dir = tmp_path / "images"
    thumbs_dir = tmp_path / "thumbs"
    area_dir = tmp_path / "area"
    mask_dir.mkdir()
    image_dir.mkdir()

    image = np.full((30, 40, 3), 220, dtype=np.uint8)
    image[5:11, 6:14, :] = np.array([40, 120, 40], dtype=np.uint8)
    image[15:24, 24:33, :] = np.array([60, 150, 60], dtype=np.uint8)
    Image.fromarray(image, mode="RGB").save(image_dir / "sample.png")

    mask = np.zeros((30, 40), dtype=np.uint8)
    mask[5:11, 6:14] = 255
    mask[15:24, 24:33] = 255
    Image.fromarray(mask, mode="L").save(mask_dir / "sample.png")

    report = extract_thumbnails_from_masks(
        full_mask_dir=mask_dir,
        source_image_dir=image_dir,
        thumbnails_dir=thumbs_dir,
        area_dir=area_dir,
        min_area=8,
        padding=2,
    )

    assert report.exported_files == ["sample_01.png", "sample_02.png"]
    area_files = sorted(p.name for p in area_dir.glob("*.png"))
    thumb_files = sorted(p.name for p in thumbs_dir.glob("*.jpg"))
    assert area_files == ["sample_01.png", "sample_02.png"]
    assert thumb_files == ["sample_01.jpg", "sample_02.jpg"]

    area_image = np.array(Image.open(area_dir / "sample_01.png").convert("L"))
    assert area_image[0, 0] == 255
    assert (area_image == 0).any()


def test_extract_thumbnails_from_masks_ignores_edge_connected_components(tmp_path: Path) -> None:
    mask_dir = tmp_path / "masks"
    image_dir = tmp_path / "images"
    thumbs_dir = tmp_path / "thumbs"
    area_dir = tmp_path / "area"
    mask_dir.mkdir()
    image_dir.mkdir()

    image = np.full((20, 20, 3), 220, dtype=np.uint8)
    Image.fromarray(image, mode="RGB").save(image_dir / "edge.png")

    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[0:4, 0:4] = 255
    mask[8:14, 8:14] = 255
    Image.fromarray(mask, mode="L").save(mask_dir / "edge.png")

    report = extract_thumbnails_from_masks(
        full_mask_dir=mask_dir,
        source_image_dir=image_dir,
        thumbnails_dir=thumbs_dir,
        area_dir=area_dir,
        min_area=8,
        padding=1,
    )

    assert report.exported_files == ["edge_01.png"]
