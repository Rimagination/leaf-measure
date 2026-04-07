from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import exposure, filters, morphology


@dataclass(frozen=True)
class FullMaskRecoveryReport:
    corrected_files: list[str]
    recovered_components: dict[str, int]


CropMaskProvider = Callable[[Path, tuple[int, int, int, int], Path], np.ndarray | None]


@dataclass(frozen=True)
class _RescueFragment:
    area: int
    bbox: tuple[int, int, int, int]


def _find_source_image(source_dir: Path, mask_name: str) -> Path | None:
    stem = Path(mask_name).stem
    matches = sorted(source_dir.glob(f"{stem}.*"))
    for match in matches:
        if match.is_file():
            return match
    return None


def _odd_block_size(value: int, *, minimum: int = 41, maximum: int = 151) -> int:
    block = max(minimum, min(maximum, value))
    if block % 2 == 0:
        block += 1
    return block


def _group_overlapping_fragments(
    fragments: list[_RescueFragment],
    *,
    padding: int,
) -> list[list[_RescueFragment]]:
    if not fragments:
        return []

    parent = list(range(len(fragments)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    def overlaps(left: _RescueFragment, right: _RescueFragment) -> bool:
        lx0, ly0, lx1, ly1 = left.bbox
        rx0, ry0, rx1, ry1 = right.bbox
        lx0 -= padding
        ly0 -= padding
        lx1 += padding
        ly1 += padding
        rx0 -= padding
        ry0 -= padding
        rx1 += padding
        ry1 += padding
        return not (lx1 < rx0 or rx1 < lx0 or ly1 < ry0 or ry1 < ly0)

    for index in range(len(fragments)):
        for other in range(index + 1, len(fragments)):
            if overlaps(fragments[index], fragments[other]):
                union(index, other)

    groups: dict[int, list[_RescueFragment]] = {}
    for index, fragment in enumerate(fragments):
        groups.setdefault(find(index), []).append(fragment)
    return list(groups.values())


def _detect_recovery_candidate_boxes(
    source_rgb: np.ndarray,
    current_white_foreground: np.ndarray,
    *,
    scale: float = 0.25,
    min_fragment_area: int = 300,
    min_group_area: int = 2_000,
    min_group_max_dim: int = 100,
    overlap_padding: int = 28,
    border_margin: int = 6,
    full_res_padding: int = 120,
) -> list[tuple[int, int, int, int]]:
    height, width = current_white_foreground.shape
    scaled_width = max(128, round(width * scale))
    scaled_height = max(128, round(height * scale))

    resized_source = np.array(
        Image.fromarray(source_rgb).resize((scaled_width, scaled_height), Image.Resampling.BILINEAR)
    )
    resized_mask = (
        np.array(
            Image.fromarray((current_white_foreground.astype(np.uint8) * 255)).resize(
                (scaled_width, scaled_height), Image.Resampling.NEAREST
            )
        )
        >= 128
    )

    gray = np.array(Image.fromarray(resized_source).convert("L"), dtype=np.uint8)
    clahe = (exposure.equalize_adapthist(gray, clip_limit=0.02) * 255).astype(np.uint8)
    local_threshold = filters.threshold_local(
        clahe,
        block_size=_odd_block_size(min(scaled_height, scaled_width) // 4, minimum=41, maximum=81),
        offset=8,
        method="gaussian",
    )
    candidates = clahe < local_threshold
    candidates = morphology.remove_small_objects(candidates, max_size=min_fragment_area - 1)
    candidates = morphology.opening(candidates, morphology.disk(1))
    candidates = morphology.closing(candidates, morphology.disk(2))
    rescue = candidates & (~morphology.dilation(resized_mask, morphology.disk(4)))
    rescue = morphology.remove_small_objects(rescue, max_size=min_fragment_area - 1)

    labels, _ = ndi.label(rescue)
    objects = ndi.find_objects(labels)
    sizes = np.bincount(labels.ravel())[1:]
    fragments: list[_RescueFragment] = []
    for index, image_slice in enumerate(objects, start=1):
        if image_slice is None:
            continue
        area = int(sizes[index - 1])
        if area < min_fragment_area:
            continue
        y0, y1 = image_slice[0].start, image_slice[0].stop
        x0, x1 = image_slice[1].start, image_slice[1].stop
        fragments.append(_RescueFragment(area=area, bbox=(x0, y0, x1, y1)))

    boxes: list[tuple[int, int, int, int]] = []
    for group in _group_overlapping_fragments(fragments, padding=overlap_padding):
        total_area = sum(fragment.area for fragment in group)
        x0 = min(fragment.bbox[0] for fragment in group)
        y0 = min(fragment.bbox[1] for fragment in group)
        x1 = max(fragment.bbox[2] for fragment in group)
        y1 = max(fragment.bbox[3] for fragment in group)
        max_dim = max(x1 - x0, y1 - y0)
        touches_border = (
            x0 <= border_margin
            or y0 <= border_margin
            or x1 >= scaled_width - border_margin
            or y1 >= scaled_height - border_margin
        )
        if total_area < min_group_area or max_dim < min_group_max_dim or touches_border:
            continue

        full_x0 = max(0, round(x0 / scale) - full_res_padding)
        full_y0 = max(0, round(y0 / scale) - full_res_padding)
        full_x1 = min(width, round(x1 / scale) + full_res_padding)
        full_y1 = min(height, round(y1 / scale) + full_res_padding)
        boxes.append((full_x0, full_y0, full_x1, full_y1))
    return boxes


def recover_missing_full_mask_leaves(
    *,
    source_image_dir: Path,
    area_dir: Path,
    target_files: list[str],
    crop_mask_provider: CropMaskProvider,
    work_dir: Path,
    min_component_area: int = 15_000,
    subtract_padding: int = 8,
) -> FullMaskRecoveryReport:
    corrected_files: list[str] = []
    recovered_components: dict[str, int] = {}
    work_dir.mkdir(parents=True, exist_ok=True)

    for mask_name in sorted(set(target_files)):
        mask_path = area_dir / mask_name
        if not mask_path.exists():
            continue
        source_path = _find_source_image(source_image_dir, mask_name)
        if source_path is None:
            continue

        source_rgb = np.array(Image.open(source_path).convert("RGB"))
        white_foreground = np.array(Image.open(mask_path).convert("L")) >= 128
        candidate_boxes = _detect_recovery_candidate_boxes(source_rgb, white_foreground)
        if not candidate_boxes:
            continue

        recovered_mask = np.zeros_like(white_foreground, dtype=bool)
        recovered_count = 0
        for index, (x0, y0, x1, y1) in enumerate(candidate_boxes, start=1):
            crop_existing = white_foreground[y0:y1, x0:x1]
            crop_work_dir = work_dir / f"{Path(mask_name).stem}_{index:02d}"
            crop_recovered = crop_mask_provider(source_path, (x0, y0, x1, y1), crop_work_dir)
            if crop_recovered is None:
                continue
            crop_recovered = np.asarray(crop_recovered, dtype=bool)
            if crop_recovered.shape != crop_existing.shape:
                raise ValueError(
                    f"Crop mask provider returned shape {crop_recovered.shape} for {mask_name}, expected {crop_existing.shape}."
                )
            crop_recovered = crop_recovered & (
                ~morphology.dilation(crop_existing, morphology.disk(subtract_padding))
            )
            crop_recovered = ndi.binary_fill_holes(crop_recovered)
            labels, _ = ndi.label(crop_recovered)
            border = np.zeros_like(crop_recovered, dtype=bool)
            border[0, :] = True
            border[-1, :] = True
            border[:, 0] = True
            border[:, -1] = True
            edge_labels = set(np.unique(labels[border])) - {0}
            component_sizes = np.bincount(labels.ravel())[1:]
            keep_labels = {
                component_index
                for component_index, component_size in enumerate(component_sizes, start=1)
                if component_index not in edge_labels and int(component_size) >= min_component_area
            }
            if not keep_labels:
                continue
            crop_recovered = np.isin(labels, list(keep_labels))
            recovered_count += len(keep_labels)
            recovered_mask[y0:y1, x0:x1] |= crop_recovered

        if recovered_count == 0:
            continue

        merged = white_foreground | recovered_mask
        Image.fromarray((merged.astype(np.uint8) * 255), mode="L").save(mask_path)
        corrected_files.append(mask_name)
        recovered_components[mask_name] = recovered_count

    return FullMaskRecoveryReport(
        corrected_files=corrected_files,
        recovered_components=recovered_components,
    )
