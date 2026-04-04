from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi


@dataclass(frozen=True)
class FullMaskCorrectionReport:
    corrected_files: list[str]


def _white_component_stats(mask: np.ndarray, *, min_area: int) -> tuple[list[int], list[int]]:
    labels, count = ndi.label(mask)
    border = np.zeros_like(mask, dtype=bool)
    border[0, :] = True
    border[-1, :] = True
    border[:, 0] = True
    border[:, -1] = True
    edge_labels = set(np.unique(labels[border])) - {0}
    component_sizes = np.bincount(labels.ravel())[1:]
    non_edge = [
        int(size)
        for index, size in enumerate(component_sizes, start=1)
        if index not in edge_labels and int(size) >= min_area
    ]
    edge = [
        int(size)
        for index, size in enumerate(component_sizes, start=1)
        if index in edge_labels and int(size) >= min_area
    ]
    return non_edge, edge


def should_correct_full_mask(path: Path, *, min_area: int = 80) -> bool:
    arr = np.array(Image.open(path).convert("L"))
    white_mask = arr > 127
    black_mask = ~white_mask

    white_non_edge, _ = _white_component_stats(white_mask, min_area=min_area)
    black_non_edge, _ = _white_component_stats(black_mask, min_area=min_area)

    if len(white_non_edge) < 20:
        return False
    if len(black_non_edge) > 2:
        return False

    black_area = int(sum(black_non_edge))
    white_area = int(sum(white_non_edge))
    return black_area > white_area * 2


def correct_full_mask(path: Path, *, min_area: int = 80) -> bool:
    arr = np.array(Image.open(path).convert("L"))
    white_mask = arr > 127

    labels, _ = ndi.label(white_mask)
    border = np.zeros_like(white_mask, dtype=bool)
    border[0, :] = True
    border[-1, :] = True
    border[:, 0] = True
    border[:, -1] = True
    edge_labels = set(np.unique(labels[border])) - {0}
    component_sizes = np.bincount(labels.ravel())[1:]

    keep_labels = {
        index
        for index, size in enumerate(component_sizes, start=1)
        if index not in edge_labels and int(size) >= min_area
    }
    if not keep_labels:
        return False

    corrected = np.isin(labels, list(keep_labels)).astype(np.uint8) * 255
    Image.fromarray(corrected, mode="L").save(path)
    return True


def correct_full_masks(area_dir: Path, *, min_area: int = 80) -> FullMaskCorrectionReport:
    corrected_files: list[str] = []
    for path in sorted(area_dir.glob("*.png")):
        if should_correct_full_mask(path, min_area=min_area) and correct_full_mask(path, min_area=min_area):
            corrected_files.append(path.name)
    return FullMaskCorrectionReport(corrected_files=corrected_files)
