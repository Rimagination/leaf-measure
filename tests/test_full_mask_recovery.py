from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

from engine.full_mask_recovery import recover_missing_full_mask_leaves


def _draw_leaf(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    *,
    scale: float = 1.0,
    angle: float = 0.0,
    fill: tuple[int, int, int] | int = (100, 120, 100),
) -> None:
    cx, cy = center
    length = int(180 * scale)
    stem_width = max(8, int(8 * scale))
    leaflet_radius_x = max(18, int(18 * scale))
    leaflet_radius_y = max(10, int(10 * scale))
    offset_start = max(18, int(18 * scale))
    offset_step = max(22, int(22 * scale))
    stem_end = (cx + length * np.cos(angle), cy + length * np.sin(angle))
    draw.line((cx, cy, *stem_end), fill=fill, width=stem_width)
    for offset in range(offset_start, length, offset_step):
        px = cx + offset * np.cos(angle)
        py = cy + offset * np.sin(angle)
        dx = leaflet_radius_x * np.sin(angle)
        dy = -leaflet_radius_x * np.cos(angle)
        for sign in (-1, 1):
            ex = px + sign * dx
            ey = py + sign * dy
            draw.ellipse(
                (
                    ex - leaflet_radius_x,
                    ey - leaflet_radius_y,
                    ex + leaflet_radius_x,
                    ey + leaflet_radius_y,
                ),
                fill=fill,
            )


def _leaf_mask(shape: tuple[int, int], centers: list[tuple[int, int]], *, scale: float = 1.0) -> np.ndarray:
    image = Image.new("L", (shape[1], shape[0]), 0)
    draw = ImageDraw.Draw(image)
    for center in centers:
        _draw_leaf(draw, center, scale=scale, fill=255)
    return np.array(image) > 0


def test_recover_missing_full_mask_leaves_restores_large_unmasked_leaf_groups(tmp_path: Path) -> None:
    source_dir = tmp_path / "input"
    area_dir = tmp_path / "area"
    source_dir.mkdir()
    area_dir.mkdir()

    scale = 2.0
    rgb = Image.new("RGB", (1200, 900), (240, 240, 240))
    draw = ImageDraw.Draw(rgb)
    centers = [(120, 120), (610, 240), (500, 550)]
    for center in centers:
        _draw_leaf(draw, center, scale=scale)
    source_path = source_dir / "input_0001.tiff"
    rgb.save(source_path)

    existing_mask = _leaf_mask((900, 1200), [centers[0]], scale=scale)
    Image.fromarray(existing_mask.astype(np.uint8) * 255, mode="L").save(area_dir / "input_0001.png")

    full_expected_mask = _leaf_mask((900, 1200), centers, scale=scale)

    def provider(source_path: Path, box: tuple[int, int, int, int], work_dir: Path) -> np.ndarray:
        x0, y0, x1, y1 = box
        return full_expected_mask[y0:y1, x0:x1]

    report = recover_missing_full_mask_leaves(
        source_image_dir=source_dir,
        area_dir=area_dir,
        target_files=["input_0001.png"],
        crop_mask_provider=provider,
        work_dir=tmp_path / "recovery_work",
        min_component_area=5_000,
    )

    assert report.corrected_files == ["input_0001.png"]
    repaired = np.array(Image.open(area_dir / "input_0001.png").convert("L")) >= 128
    labels, _ = ndi.label(repaired)
    sizes = np.bincount(labels.ravel())[1:]
    assert sum(size >= 5_000 for size in sizes) >= 3


def test_recover_missing_full_mask_leaves_skips_when_no_candidates_exist(tmp_path: Path) -> None:
    source_dir = tmp_path / "input"
    area_dir = tmp_path / "area"
    source_dir.mkdir()
    area_dir.mkdir()

    rgb = Image.new("RGB", (400, 300), (240, 240, 240))
    draw = ImageDraw.Draw(rgb)
    center = (120, 120)
    _draw_leaf(draw, center)
    source_path = source_dir / "input_0001.tiff"
    rgb.save(source_path)

    existing_mask = _leaf_mask((300, 400), [center])
    Image.fromarray(existing_mask.astype(np.uint8) * 255, mode="L").save(area_dir / "input_0001.png")

    provider_calls = 0

    def provider(source_path: Path, box: tuple[int, int, int, int], work_dir: Path) -> np.ndarray:
        nonlocal provider_calls
        provider_calls += 1
        x0, y0, x1, y1 = box
        return existing_mask[y0:y1, x0:x1]

    report = recover_missing_full_mask_leaves(
        source_image_dir=source_dir,
        area_dir=area_dir,
        target_files=["input_0001.png"],
        crop_mask_provider=provider,
        work_dir=tmp_path / "recovery_work",
    )

    assert report.corrected_files == []
    assert provider_calls == 0
    repaired = np.array(Image.open(area_dir / "input_0001.png").convert("L")) >= 128
    np.testing.assert_array_equal(repaired, existing_mask)
