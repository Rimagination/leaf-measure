from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi


@dataclass(frozen=True)
class ThumbnailExtractionReport:
    exported_files: list[str]


def _source_image_index(source_image_dir: Path) -> dict[str, Path]:
    return {
        path.stem: path
        for path in sorted(source_image_dir.iterdir())
        if path.is_file() and not path.name.startswith(".")
    }


def _component_records(mask: np.ndarray, *, min_area: int) -> list[tuple[int, tuple[int, int, int, int]]]:
    labels, count = ndi.label(mask)
    border = np.zeros_like(mask, dtype=bool)
    border[0, :] = True
    border[-1, :] = True
    border[:, 0] = True
    border[:, -1] = True
    edge_labels = set(np.unique(labels[border])) - {0}

    records: list[tuple[int, tuple[int, int, int, int]]] = []
    for label in range(1, count + 1):
        if label in edge_labels:
            continue
        ys, xs = np.where(labels == label)
        area = len(xs)
        if area < min_area:
            continue
        records.append((label, (int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max()))))

    records.sort(key=lambda item: (item[1][0], item[1][2]))
    return records


def extract_thumbnails_from_masks(
    *,
    full_mask_dir: Path,
    source_image_dir: Path,
    thumbnails_dir: Path,
    area_dir: Path,
    min_area: int = 80,
    padding: int = 3,
) -> ThumbnailExtractionReport:
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    area_dir.mkdir(parents=True, exist_ok=True)
    source_images = _source_image_index(source_image_dir)
    exported_files: list[str] = []

    for mask_path in sorted(full_mask_dir.glob("*.png")):
        source_path = source_images.get(mask_path.stem)
        if source_path is None:
            continue

        full_mask = np.array(Image.open(mask_path).convert("L")) > 127
        source_image = np.array(Image.open(source_path).convert("RGB"))
        height, width = full_mask.shape
        records = _component_records(full_mask, min_area=min_area)
        width_digits = max(2, len(str(len(records))))

        labels, _ = ndi.label(full_mask)
        for index, (label, (y0, y1, x0, x1)) in enumerate(records, start=1):
            pad_y0 = max(0, y0 - padding)
            pad_y1 = min(height - 1, y1 + padding)
            pad_x0 = max(0, x0 - padding)
            pad_x1 = min(width - 1, x1 + padding)
            component = labels[pad_y0 : pad_y1 + 1, pad_x0 : pad_x1 + 1] == label
            crop = source_image[pad_y0 : pad_y1 + 1, pad_x0 : pad_x1 + 1].copy()
            crop[~component] = 255

            area_crop = np.full(component.shape, 255, dtype=np.uint8)
            area_crop[component] = 0

            suffix = f"{index:0{width_digits}d}"
            stem = f"{mask_path.stem}_{suffix}"
            Image.fromarray(crop, mode="RGB").save(thumbnails_dir / f"{stem}.jpg", quality=95)
            Image.fromarray(area_crop, mode="L").save(area_dir / f"{stem}.png")
            exported_files.append(f"{stem}.png")

    return ThumbnailExtractionReport(exported_files=exported_files)
