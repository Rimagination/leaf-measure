from __future__ import annotations

from pathlib import Path

from PIL import Image


def _coerce_pair(value: object) -> tuple[float, float] | None:
    if isinstance(value, tuple) and len(value) >= 2:
        try:
            return float(value[0]), float(value[1])
        except (TypeError, ValueError):
            return None
    return None


def read_image_dpi(path: Path) -> tuple[float, float] | None:
    with Image.open(path) as image:
        dpi = _coerce_pair(image.info.get("dpi"))
        if dpi:
            return dpi

        tags = getattr(image, "tag_v2", None)
        if tags is None:
            return None

        x_res = tags.get(282)
        y_res = tags.get(283)
        unit = tags.get(296)
        raw_pair = _coerce_pair((x_res, y_res))
        if raw_pair is None:
            return None
        if unit == 3:
            return raw_pair[0] * 2.54, raw_pair[1] * 2.54
        return raw_pair


def collect_dpi_metadata(input_dir: Path) -> dict[str, tuple[float, float] | None]:
    metadata: dict[str, tuple[float, float] | None] = {}
    for path in sorted(input_dir.iterdir()):
        if not path.is_file():
            continue
        try:
            metadata[path.name] = read_image_dpi(path)
        except Exception:
            metadata[path.name] = None
    return metadata

