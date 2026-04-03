# Method Summary

`leaf-measure` executes the published Fiji-based FAMeLeS workflow for automated leaf morphology measurement.

The workflow measures:

- area
- perimeter
- length
- width
- circularity
- solidity

The current product supports two FAMeLeS modes:

- `Full image`: keeps whole-image layout and writes one results table covering all detected leaf objects in each image.
- `Thumbnails`: additionally exports each detected leaf object as its own cropped artifact, along with per-leaf binary and outline outputs.

Default units are pixels. If image DPI metadata is available, the product reports it and explains how to convert pixel outputs into physical units.

