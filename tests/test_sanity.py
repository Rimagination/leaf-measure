from __future__ import annotations

import pandas as pd

from engine.sanity import full_image_sanity_warnings


def test_full_image_sanity_warns_when_largest_object_is_too_large() -> None:
    frame = pd.DataFrame(
        {
            "Label": ["scan.png", "scan.png", "other.png"],
            "Area": [8000, 50, 1000],
        }
    )

    warnings = full_image_sanity_warnings(
        frame,
        image_areas={"scan.png": 10000, "other.png": 20000},
        max_ratio=0.7,
    )

    assert len(warnings) == 1
    assert "scan.png" in warnings[0]
    assert "80.0%" in warnings[0]
