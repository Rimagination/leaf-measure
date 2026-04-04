from __future__ import annotations

from pathlib import Path

import pandas as pd
from PIL import Image


def image_area_map(image_dir: Path) -> dict[str, int]:
    areas: dict[str, int] = {}
    for path in sorted(image_dir.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        try:
            width, height = Image.open(path).size
        except OSError:
            continue
        areas[path.name] = width * height
        areas[path.stem] = width * height
    return areas


def full_image_sanity_warnings(
    results_frame: pd.DataFrame,
    *,
    image_areas: dict[str, int],
    max_ratio: float = 0.7,
) -> list[str]:
    if "Label" not in results_frame.columns or "Area" not in results_frame.columns:
        return []

    frame = results_frame.copy()
    frame["Area"] = pd.to_numeric(frame["Area"], errors="coerce")
    warnings: list[str] = []
    for label, group in frame.groupby("Label"):
        image_area = image_areas.get(str(label))
        if not image_area:
            continue
        largest_area = float(group["Area"].max())
        ratio = largest_area / float(image_area)
        if ratio >= max_ratio:
            warnings.append(
                f"Full image sanity check: the largest object for `{label}` covers {ratio:.1%} of the image area. "
                "This may indicate background was measured as a leaf object; review the binary and outline outputs."
            )
    return warnings
