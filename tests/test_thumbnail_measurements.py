from __future__ import annotations

from pathlib import Path

import pandas as pd
import numpy as np
from PIL import Image

from engine.thumbnail_measurements import write_thumbnail_results_csv


def test_write_thumbnail_results_csv_measures_single_leaf_masks(tmp_path: Path) -> None:
    area_dir = tmp_path / "area"
    area_dir.mkdir()

    image = np.full((20, 20), 255, dtype=np.uint8)
    image[5:15, 7:13] = 0
    Image.fromarray(image, mode="L").save(area_dir / "leaf_01.png")

    results_csv = tmp_path / "results.csv"
    write_thumbnail_results_csv(area_dir=area_dir, results_csv=results_csv)

    frame = pd.read_csv(results_csv)
    assert list(frame.columns) == ["Label", "Area", "Perim.", "Circ.", "Length", "Width ", "Solidity"]
    assert frame.loc[0, "Label"] == "leaf_01.png"
    assert int(frame.loc[0, "Area"]) == 60
    assert float(frame.loc[0, "Length"]) > float(frame.loc[0, "Width "])
    assert abs(float(frame.loc[0, "Solidity"]) - 1.0) < 1e-6
