from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi


@dataclass(frozen=True)
class FullMaskPolarityDecision:
    should_invert: bool
    current_component_count: int
    inverted_component_count: int
    current_largest_component_area_ratio: float
    inverted_largest_component_area_ratio: float
    current_source_score: float | None = None
    inverted_source_score: float | None = None


@dataclass(frozen=True)
class FullMaskPolarityReport:
    invert_files: list[str]


def _component_stats(mask: np.ndarray, *, min_area: int) -> tuple[int, int, np.ndarray]:
    labels, _ = ndi.label(mask)
    border = np.zeros_like(mask, dtype=bool)
    border[0, :] = True
    border[-1, :] = True
    border[:, 0] = True
    border[:, -1] = True
    edge_labels = set(np.unique(labels[border])) - {0}
    component_sizes = np.bincount(labels.ravel())[1:]
    keep_labels = [
        index
        for index, size in enumerate(component_sizes, start=1)
        if index not in edge_labels and int(size) >= min_area
    ]
    if not keep_labels:
        return 0, 0, np.zeros_like(mask, dtype=bool)
    valid_sizes = [int(component_sizes[index - 1]) for index in keep_labels]
    kept_mask = np.isin(labels, keep_labels)
    return len(valid_sizes), max(valid_sizes), kept_mask


def _source_foreground_score(source_gray: np.ndarray, component_mask: np.ndarray) -> float | None:
    if not component_mask.any():
        return None
    border = np.zeros_like(component_mask, dtype=bool)
    border[0, :] = True
    border[-1, :] = True
    border[:, 0] = True
    border[:, -1] = True
    background_values = source_gray[border]
    if background_values.size == 0:
        return None
    return float(background_values.mean() - source_gray[component_mask].mean())


def analyze_full_measurement_mask_polarity(
    path: Path,
    *,
    min_area: int = 80,
    min_largest_component_ratio: float = 0.5,
    min_inverted_components: int = 2,
    source_path: Path | None = None,
    min_source_score_margin: float = 8.0,
    min_source_foreground_score: float = 10.0,
) -> FullMaskPolarityDecision:
    image = np.array(Image.open(path).convert("L"))
    image_area = int(image.shape[0] * image.shape[1])
    current_mask = image < 128
    inverted_mask = image >= 128

    current_count, current_largest, current_component_mask = _component_stats(current_mask, min_area=min_area)
    inverted_count, inverted_largest, inverted_component_mask = _component_stats(inverted_mask, min_area=min_area)
    current_ratio = current_largest / float(image_area) if image_area else 0.0
    inverted_ratio = inverted_largest / float(image_area) if image_area else 0.0

    should_invert = (
        current_count > inverted_count
        and inverted_count >= min_inverted_components
        and current_ratio >= min_largest_component_ratio
    )
    current_source_score: float | None = None
    inverted_source_score: float | None = None
    if source_path is not None and source_path.exists():
        source_gray = np.array(Image.open(source_path).convert("L"))
        if source_gray.shape != image.shape:
            source_gray = np.array(
                Image.fromarray(source_gray).resize((image.shape[1], image.shape[0]), Image.Resampling.BILINEAR)
            )
        current_source_score = _source_foreground_score(source_gray, current_component_mask)
        inverted_source_score = _source_foreground_score(source_gray, inverted_component_mask)
        if (
            not should_invert
            and current_ratio >= min_largest_component_ratio
            and inverted_count >= 1
            and inverted_source_score is not None
            and current_source_score is not None
            and inverted_source_score >= min_source_foreground_score
            and inverted_source_score > current_source_score + min_source_score_margin
        ):
            should_invert = True
    return FullMaskPolarityDecision(
        should_invert=should_invert,
        current_component_count=current_count,
        inverted_component_count=inverted_count,
        current_largest_component_area_ratio=current_ratio,
        inverted_largest_component_area_ratio=inverted_ratio,
        current_source_score=current_source_score,
        inverted_source_score=inverted_source_score,
    )


def select_full_measurement_inversion_files(
    area_dir: Path,
    *,
    min_area: int = 80,
    source_image_dir: Path | None = None,
) -> FullMaskPolarityReport:
    invert_files: list[str] = []
    for path in sorted(area_dir.glob("*.png")):
        source_path: Path | None = None
        if source_image_dir is not None:
            matches = sorted(source_image_dir.glob(f"{path.stem}.*"))
            for match in matches:
                if match.is_file():
                    source_path = match
                    break
        decision = analyze_full_measurement_mask_polarity(path, min_area=min_area, source_path=source_path)
        if not decision.should_invert:
            continue
        invert_files.append(path.name)
    return FullMaskPolarityReport(invert_files=invert_files)
