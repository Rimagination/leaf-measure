from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import shutil

import numpy as np
from PIL import Image


SUPPORTED_INPUT_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


@dataclass(frozen=True)
class StageInputReport:
    staged_dir: Path
    modified_files: list[str]


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


def stage_input_images(input_dir: Path, staged_dir: Path) -> StageInputReport:
    staged_dir.mkdir(parents=True, exist_ok=True)
    modified_files: list[str] = []

    for source in sorted(input_dir.iterdir()):
        if (
            not source.is_file()
            or source.name.startswith(".")
            or source.suffix.lower() not in SUPPORTED_INPUT_SUFFIXES
        ):
            continue

        destination = staged_dir / source.name
        sanitized, changed = _sanitize_dark_edge_artifacts(source)
        if changed and sanitized is not None:
            Image.fromarray(sanitized, mode="RGB").save(destination)
            modified_files.append(source.name)
        else:
            shutil.copy2(source, destination)

    return StageInputReport(staged_dir=staged_dir, modified_files=modified_files)
