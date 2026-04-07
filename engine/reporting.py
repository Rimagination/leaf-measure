from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from engine.preprocess import restore_staged_name


TRAIT_DEFINITIONS = {
    "Area": "Projected leaf area measured from the binary segmentation.",
    "Perim.": "Leaf perimeter measured from the segmented object boundary.",
    "Length": "Leaf length derived from the Feret diameter reported by Fiji.",
    "Width ": "Leaf width derived from the minimum Feret diameter reported by Fiji.",
    "Circ.": "Circularity computed by Fiji from area and perimeter.",
    "Solidity": "Solidity computed as area divided by convex area.",
}


def normalize_results_csv(path: Path) -> pd.DataFrame:
    encodings = ("utf-8", "utf-8-sig", "gb18030", "gbk")
    frame: pd.DataFrame | None = None
    last_error: UnicodeDecodeError | None = None
    for encoding in encodings:
        try:
            frame = pd.read_csv(path, encoding=encoding)
            break
        except UnicodeDecodeError as error:
            last_error = error
    if frame is None:
        assert last_error is not None
        raise last_error
    drop_columns = [
        column
        for column in frame.columns
        if column.startswith("Unnamed:") or not str(column).strip()
    ]
    if "Mean" in frame.columns:
        drop_columns.append("Mean")
    if drop_columns:
        frame = frame.drop(columns=drop_columns)
    if "Label" in frame.columns:
        frame["Label"] = frame["Label"].fillna("").astype(str)
        frame = frame[frame["Label"].str.strip() != ""].reset_index(drop=True)
    frame.to_csv(path, index=False)
    return frame


@dataclass(frozen=True)
class FullImageFilterReport:
    dropped_rows: list[dict[str, object]]


def remap_results_labels(path: Path, filename_map: dict[str, str]) -> pd.DataFrame | None:
    if not filename_map or not path.exists():
        return None

    frame = normalize_results_csv(path)
    if "Label" in frame.columns:
        frame["Label"] = frame["Label"].map(lambda value: restore_staged_name(str(value), filename_map))
    frame.to_csv(path, index=False)
    return frame


def _edge_connected_component_areas(mask: np.ndarray) -> list[int]:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    areas: list[int] = []

    for y in range(height):
        for x in range(width):
            if not mask[y, x] or visited[y, x]:
                continue
            if 0 < y < height - 1 and 0 < x < width - 1:
                continue
            queue: deque[tuple[int, int]] = deque([(y, x)])
            visited[y, x] = True
            area = 0
            while queue:
                cy, cx = queue.popleft()
                area += 1
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if (
                        0 <= ny < height
                        and 0 <= nx < width
                        and mask[ny, nx]
                        and not visited[ny, nx]
                    ):
                        visited[ny, nx] = True
                        queue.append((ny, nx))
            areas.append(area)
    return sorted(areas, reverse=True)


def filter_full_image_results(
    frame: pd.DataFrame,
    *,
    area_dir: Path,
    min_background_ratio: float = 0.5,
    area_tolerance_ratio: float = 0.02,
    dominance_ratio: float = 5.0,
) -> tuple[pd.DataFrame, FullImageFilterReport]:
    if "Label" not in frame.columns or "Area" not in frame.columns:
        return frame.copy(), FullImageFilterReport(dropped_rows=[])

    working = frame.copy()
    working["Area"] = pd.to_numeric(working["Area"], errors="coerce")
    kept_indexes: list[int] = []
    dropped_rows: list[dict[str, object]] = []

    for label, group in working.groupby("Label", sort=False):
        if len(group) < 2:
            kept_indexes.extend(group.index.tolist())
            continue
        image_path = area_dir / str(label)
        if not image_path.exists():
            alt_path = area_dir / f"{label}.png"
            image_path = alt_path if alt_path.exists() else image_path
        if not image_path.exists():
            kept_indexes.extend(group.index.tolist())
            continue

        image = np.array(Image.open(image_path).convert("L"))
        image_area = int(image.shape[0] * image.shape[1])
        background_candidates: list[int] = []
        background_candidates.extend([int((image >= 128).sum()), int((image < 128).sum())])
        for mask in (image >= 128, image < 128):
            background_candidates.extend(_edge_connected_component_areas(mask))
        background_candidates = [
            candidate for candidate in background_candidates if candidate >= image_area * min_background_ratio
        ]

        drop_index: int | None = None
        sorted_areas = group["Area"].dropna().sort_values(ascending=False).tolist()
        second_largest = float(sorted_areas[1]) if len(sorted_areas) > 1 else 0.0
        for candidate_area in sorted(set(background_candidates), reverse=True):
            tolerance = max(32, round(candidate_area * area_tolerance_ratio))
            matches = group.index[(group["Area"] - candidate_area).abs() <= tolerance]
            if len(matches) == 0:
                continue
            candidate_index = int(group.loc[matches].sort_values("Area", ascending=False).index[0])
            candidate_value = float(group.loc[candidate_index, "Area"])
            if second_largest > 0 and candidate_value < second_largest * dominance_ratio:
                continue
            drop_index = candidate_index
            break

        if drop_index is not None:
            dropped_rows.append(frame.loc[drop_index].to_dict())
            group = group.drop(index=drop_index)
        kept_indexes.extend(group.index.tolist())

    filtered = frame.loc[kept_indexes].reset_index(drop=True)
    return filtered, FullImageFilterReport(dropped_rows=dropped_rows)


def write_method_summary(path: Path, *, mode: str, executor: str, repair_note: str | None = None) -> None:
    text = (
        "# Method Summary\n\n"
        "This run executed the Fiji-based FAMeLeS workflow through the leaf-measure engine.\n\n"
        f"- Mode: `{mode}`\n"
        f"- Executor: `{executor}`\n"
        "- Default unit: pixels\n"
        "- Physical-unit conversion is not applied automatically\n"
    )
    if repair_note:
        text += f"- Repair behavior: {repair_note}\n"
    path.write_text(text, encoding="utf-8")


def write_trait_explanations(path: Path) -> None:
    lines = ["# Trait Explanations", ""]
    for name, definition in TRAIT_DEFINITIONS.items():
        lines.append(f"- `{name}`: {definition}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_run_summary(
    path: Path,
    *,
    mode: str,
    executor: str,
    image_count: int,
    dpi_metadata: dict[str, tuple[float, float] | None],
    warnings: list[str],
) -> None:
    lines = [
        "# Run Summary",
        "",
        f"- Mode: `{mode}`",
        f"- Executor: `{executor}`",
        f"- Image count: `{image_count}`",
        "- Unit note: measurements are reported in pixels by default",
    ]
    if any(value is not None for value in dpi_metadata.values()):
        lines.append("- DPI metadata: found for at least one image")
    else:
        lines.append("- DPI metadata: not found")
    if warnings:
        lines.append("- Warnings:")
        for warning in warnings:
            lines.append(f"  - {warning}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, payload: dict) -> None:
    def default(value: object):
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, tuple):
            return list(value)
        raise TypeError(f"Unsupported manifest value: {value!r}")

    path.write_text(json.dumps(payload, indent=2, default=default), encoding="utf-8")
