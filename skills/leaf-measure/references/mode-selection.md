# Mode Selection

Choose `Full image` when the user wants one analysis pass over each whole image and does not need per-leaf cropped exports.

Choose `Thumbnails` when the user also wants each detected leaf exported as its own cropped artifact.

Concrete example:

- `Full image`: one source image contains 5 leaves, and the run produces one results table with 5 measured rows for that image plus one binary image and one outline image for the full scene.
- `Thumbnails`: the same source image still produces 5 measured rows, but it also exports 5 individual leaf crops plus per-leaf binary and outline artifacts.

