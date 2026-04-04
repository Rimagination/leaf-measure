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

For normal images, `leaf-measure` keeps the original FAMeLeS execution path.

- In `Full image` mode, repair is triggered when the binary mask shows an edge-connected background artifact enclosing many interior leaf objects.
- In `Thumbnails` mode, the workflow uses a lightweight preflight on the source image to detect strong dark-edge artifacts. Affected scans go directly to the stable repair path; unaffected scans keep the original FAMeLeS thumbnails macro path.

This is intended to fix scanner-border and polarity-related failures without silently changing the published workflow on unaffected inputs, and without paying a full-image probe cost on clean thumbnail runs.

For user-facing outputs in `Thumbnails` mode, `leaf-measure` separates two reporting layers:

- `results.csv`: one row per exported thumbnail artifact
- `results_fameles_particles_raw.csv`: the original particle-level table when the published FAMeLeS second-stage measurement reports multiple particles inside a single exported thumbnail

This keeps the original Fiji particle table available for traceability while giving end users a one-thumbnail-one-row table by default.

For setup, the repository now exposes two public helper commands:

- `python -m engine.cli fetch-assets`: download the public Figshare macros and `Trial.zip`, then stage them into `.leaf-measure-assets/`
- `python -m engine.cli fetch-fiji`: download the latest Fiji distribution into `fiji-latest-win64-jdk/`

On Windows, `.\scripts\bootstrap.ps1` uses those commands automatically when the current machine is missing upstream assets or Fiji.

For skill layout, `skills/leaf-fameles/` is now the canonical source. The repo-local host copies under `.agents/skills/leaf-fameles/` and `.claude/skills/leaf-fameles/` are generated from that source via `python -m engine.cli sync-skills` or `.\scripts\sync-skills.ps1`.
