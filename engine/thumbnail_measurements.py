from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from scipy.spatial import ConvexHull, QhullError, distance
from skimage.measure import find_contours, label, perimeter, regionprops


RESULT_COLUMNS = ["Label", "Area", "Perim.", "Circ.", "Length", "Width ", "Solidity"]


def _feret_diameters(mask: np.ndarray) -> tuple[float, float]:
    contours = find_contours(mask.astype(float), 0.5)
    if not contours:
        return 0.0, 0.0

    contour = max(contours, key=len)
    points = np.column_stack([contour[:, 1], contour[:, 0]])
    if len(points) < 2:
        return 0.0, 0.0
    if len(points) == 2:
        dist = float(np.linalg.norm(points[1] - points[0]))
        return dist, dist

    try:
        hull = ConvexHull(points)
        hull_points = points[hull.vertices]
    except QhullError:
        hull_points = points

    if len(hull_points) < 2:
        return 0.0, 0.0

    max_feret = float(distance.pdist(hull_points).max()) if len(hull_points) > 2 else float(
        np.linalg.norm(hull_points[1] - hull_points[0])
    )

    min_feret = math.inf
    rolled = np.roll(hull_points, -1, axis=0)
    for start, end in zip(hull_points, rolled):
        edge = end - start
        norm = np.linalg.norm(edge)
        if norm == 0:
            continue
        normal = np.array([-edge[1], edge[0]]) / norm
        projection = hull_points @ normal
        width = float(projection.max() - projection.min())
        min_feret = min(min_feret, width)

    if not math.isfinite(min_feret):
        min_feret = max_feret
    return max_feret, float(min_feret)


def _measure_thumbnail(path: Path) -> dict[str, object] | None:
    arr = np.array(Image.open(path).convert("L"))
    mask = arr < 128
    if not mask.any():
        return None

    labeled = label(mask)
    props = max(regionprops(labeled), key=lambda region: region.area)
    binary = labeled == props.label
    perim = float(perimeter(binary, neighborhood=8))
    area = int(props.area)
    length, width = _feret_diameters(binary)
    circularity = 0.0 if perim == 0 else float(4.0 * math.pi * area / (perim * perim))
    solidity = float(props.solidity)

    return {
        "Label": path.name,
        "Area": area,
        "Perim.": round(perim, 2),
        "Circ.": round(circularity, 2),
        "Length": round(length, 2),
        "Width ": round(width, 2),
        "Solidity": round(solidity, 2),
    }


def write_thumbnail_results_csv(*, area_dir: Path, results_csv: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(area_dir.glob("*.png")):
        row = _measure_thumbnail(path)
        if row is not None:
            rows.append(row)

    frame = pd.DataFrame(rows, columns=RESULT_COLUMNS)
    frame.to_csv(results_csv, index=False)
    return frame
