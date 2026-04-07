from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
import shutil

import numpy as np
from PIL import Image


SUPPORTED_INPUT_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


@dataclass(frozen=True)
class StageInputReport:
    staged_dir: Path
    modified_files: list[str]
    filename_map: dict[str, str] = field(default_factory=dict)


def should_prefer_thumbnail_repair(report: StageInputReport) -> bool:
    return bool(report.modified_files)


def _dark_edge_threshold(gray: np.ndarray) -> float | None:
    height, width = gray.shape
    band = max(16, round(min(height, width) * 0.03))
    border_pixels = np.concatenate(
        [
            gray[:band, :].ravel(),
            gray[-band:, :].ravel(),
            gray[:, :band].ravel(),
            gray[:, -band:].ravel(),
        ]
    )
    low_p2 = float(np.percentile(border_pixels, 2))
    if low_p2 >= 120:
        return None
    return min(140.0, float(np.percentile(border_pixels, 3)) + 15.0)


def _edge_connected_dark_mask(gray: np.ndarray, threshold: float) -> np.ndarray:
    dark = gray <= threshold
    height, width = dark.shape
    visited = np.zeros_like(dark, dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    def seed(y: int, x: int) -> None:
        if dark[y, x] and not visited[y, x]:
            visited[y, x] = True
            queue.append((y, x))

    for x in range(width):
        seed(0, x)
        seed(height - 1, x)
    for y in range(height):
        seed(y, 0)
        seed(y, width - 1)

    while queue:
        y, x = queue.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < height and 0 <= nx < width and dark[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))

    return visited


def _sanitize_dark_edge_artifacts(source: Path) -> tuple[np.ndarray | None, bool]:
    rgb = np.array(Image.open(source).convert("RGB"))
    gray = rgb.mean(axis=2)
    threshold = _dark_edge_threshold(gray)
    if threshold is None:
        return None, False

    edge_mask = _edge_connected_dark_mask(gray, threshold)
    if not edge_mask.any():
        return None, False

    sanitized = rgb.copy()
    sanitized[edge_mask] = 255
    return sanitized, True


def _stage_name(index: int, source: Path) -> str:
    if source.name.isascii():
        return source.name
    return f"input_{index:04d}{source.suffix.lower()}"


def restore_staged_name(name: str, filename_map: dict[str, str]) -> str:
    if not filename_map:
        return name
    direct = filename_map.get(name)
    if direct is not None:
        return direct

    for staged_name, original_name in filename_map.items():
        staged_stem = Path(staged_name).stem
        original_stem = Path(original_name).stem
        if Path(name).stem == staged_stem and Path(name).suffix:
            return f"{original_stem}{Path(name).suffix}"
        if name == staged_stem:
            return original_stem
        if name.startswith(f"{staged_stem}_"):
            return f"{original_stem}{name[len(staged_stem):]}"
    return name


def restore_output_filenames(output_dirs: list[Path], filename_map: dict[str, str]) -> None:
    if not filename_map:
        return

    for output_dir in output_dirs:
        if not output_dir.exists():
            continue
        for path in sorted(output_dir.iterdir()):
            if not path.is_file():
                continue
            restored_name = restore_staged_name(path.name, filename_map)
            if restored_name == path.name:
                continue
            path.rename(path.with_name(restored_name))


def stage_input_images(input_dir: Path, staged_dir: Path) -> StageInputReport:
    staged_dir.mkdir(parents=True, exist_ok=True)
    modified_files: list[str] = []
    filename_map: dict[str, str] = {}

    for index, source in enumerate(sorted(input_dir.iterdir()), start=1):
        if (
            not source.is_file()
            or source.name.startswith(".")
            or source.suffix.lower() not in SUPPORTED_INPUT_SUFFIXES
        ):
            continue

        staged_name = _stage_name(index, source)
        filename_map[staged_name] = source.name
        destination = staged_dir / staged_name
        sanitized, changed = _sanitize_dark_edge_artifacts(source)
        if changed and sanitized is not None:
            Image.fromarray(sanitized, mode="RGB").save(destination)
            modified_files.append(source.name)
        else:
            shutil.copy2(source, destination)

    return StageInputReport(
        staged_dir=staged_dir,
        modified_files=modified_files,
        filename_map=filename_map,
    )
