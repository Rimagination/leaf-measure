from __future__ import annotations

from pathlib import Path

import pandas as pd
from PIL import Image

from engine.reporting import filter_full_image_results, normalize_results_csv


def test_normalize_results_csv_reads_gb18030(tmp_path: Path) -> None:
    csv_path = tmp_path / "results.csv"
    csv_path.write_bytes("Label,Area\n叶片样本.png,123\n".encode("gb18030"))

    frame = normalize_results_csv(csv_path)

    assert list(frame["Label"]) == ["叶片样本.png"]
    assert "叶片样本.png" in csv_path.read_text(encoding="utf-8")


def test_filter_full_image_results_drops_large_edge_connected_background_rows(tmp_path: Path) -> None:
    area_dir = tmp_path / "02_area"
    area_dir.mkdir()
    mask = Image.new("L", (10, 10), color=0)
    for x in range(3, 7):
        for y in range(3, 7):
            mask.putpixel((x, y), 255)
    mask.save(area_dir / "sample.png")

    raw = pd.DataFrame(
        [
            {"Label": "sample.png", "Area": 84, "Perim.": 40.0, "Circ.": 0.1, "Length": 10.0, "Width ": 8.0, "Solidity": 0.8},
            {"Label": "sample.png", "Area": 16, "Perim.": 18.0, "Circ.": 0.6, "Length": 4.0, "Width ": 4.0, "Solidity": 0.9},
        ]
    )

    filtered, report = filter_full_image_results(raw, area_dir=area_dir)

    assert list(filtered["Area"]) == [16]
    assert report.dropped_rows[0]["Label"] == "sample.png"
    assert int(report.dropped_rows[0]["Area"]) == 84
