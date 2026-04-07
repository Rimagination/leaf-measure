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
- In sparse or single-object edge cases, `leaf-measure` may also compare the two possible mask polarities against the source image itself and keep the polarity whose foreground pixels better match the darker leaf material.
- In `Thumbnails` mode, the workflow uses a lightweight preflight on the source image to detect strong dark-edge artifacts. Affected scans go directly to the stable repair path; unaffected scans keep the original FAMeLeS thumbnails macro path.

This is intended to fix scanner-border and polarity-related failures without silently changing the published workflow on unaffected inputs, and without paying a full-image probe cost on clean thumbnail runs.

For user-facing outputs in `Thumbnails` mode, `leaf-measure` separates two reporting layers:

- `results.csv`: one row per exported thumbnail artifact
- `results_fameles_particles_raw.csv`: the original particle-level table when the published FAMeLeS second-stage measurement reports multiple particles inside a single exported thumbnail

This keeps the original Fiji particle table available for traceability while giving end users a one-thumbnail-one-row table by default.

For `Full image`, the same split now exists when needed:

- `results.csv`: the user-facing table after correcting hole-dominated mask polarity when needed, then filtering an obviously oversized background particle from the final report
- `results_fameles_particles_raw.csv`: the untouched Fiji measurement table

This preserves published-method traceability while preventing two known full-image failure modes from dominating the user-facing report:

- a single oversized background row
- compound-leaf masks whose internal voids would otherwise be measured instead of the compound leaves

For the same narrow class of repaired full-image masks, `leaf-measure` may also add a conservative crop-rescue pass before the user-facing re-measurement step. In that pass, `leaf-measure` reruns the original FAMeLeS `Full image` macro on a small number of candidate crop regions and only merges newly recovered, non-edge-touching foreground objects back into the repaired full-image mask. This does not change the original raw Fiji table.

For setup, the repository now exposes two public helper commands:

- `python -m engine.cli fetch-assets`: download the public Figshare macros and `Trial.zip`, then stage them into `.leaf-measure-assets/`
- `python -m engine.cli fetch-fiji`: download the latest Fiji distribution into `fiji-latest-win64-jdk/`

On Windows, `.\scripts\bootstrap.ps1` uses those commands automatically when the current machine is missing upstream assets or Fiji.

Runtime discovery is intentionally conservative and shared between `doctor` and `analyze`:

- `--fiji` may point to either a Fiji directory or a launcher such as `ImageJ-win64.exe`, `ImageJ.exe`, or `fiji-windows-x64.exe`
- Fiji resolution order is: CLI path, environment variable, `config/runtime.toml`, `PATH`, common install locations, then the cached last-known-good launcher
- non-ASCII input names are staged to ASCII-safe temporary names before Fiji runs and restored in final outputs

For skill layout, `skills/leaf-measure/` is now the canonical source. The repo-local host copies under `.agents/skills/leaf-measure/` and `.claude/skills/leaf-measure/` are generated from that source via `python -m engine.cli sync-skills` or `.\scripts\sync-skills.ps1`.
