# Known Limitations

- Default units are pixels. DPI metadata may be read, but values are not auto-converted unless a later feature explicitly adds that behavior.
- `PyImageJ headless` is not a supported default path for this workflow.
- `PyImageJ interactive` is platform-sensitive:
  - on macOS it requires a GUI-capable session
  - on Linux servers or containers it typically requires a virtual display such as `Xvfb`
- `Thumbnails` mode depends on legacy ImageJ behavior and should be treated as display-sensitive until validated on the target environment.
- Real segmentation quality still depends on image quality, contrast, and background conditions.

