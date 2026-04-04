from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from engine.mask_correction import correct_full_mask, should_correct_full_mask


def test_should_correct_full_mask_detects_edge_connected_background_case(tmp_path: Path) -> None:
    image = np.zeros((60, 60), dtype=np.uint8)
    image[0, :] = 255
    image[-1, :] = 255
    image[:, 0] = 255
    image[:, -1] = 255
    for y in range(8, 52, 10):
        for x in range(8, 52, 10):
            image[y : y + 4, x : x + 4] = 255
    path = tmp_path / "mask.png"
    Image.fromarray(image, mode="L").save(path)

    assert should_correct_full_mask(path, min_area=8)
    assert correct_full_mask(path, min_area=8)

    corrected = np.array(Image.open(path).convert("L"))
    assert corrected[0, 0] == 0
    assert corrected[10, 10] == 255


def test_should_correct_full_mask_skips_reasonable_binary_masks(tmp_path: Path) -> None:
    image = np.zeros((60, 60), dtype=np.uint8)
    image[10:20, 10:20] = 255
    image[30:40, 30:40] = 255
    path = tmp_path / "clean_mask.png"
    Image.fromarray(image, mode="L").save(path)

    assert not should_correct_full_mask(path, min_area=8)
