# Artifact Handling

`leaf-measure` keeps the published FAMeLeS path by default.

If the machine is missing upstream macros or Fiji, prefer `.\scripts\bootstrap.ps1` first. It installs the current Python dependencies and fetches missing public runtime assets before analysis.

Automatic repair depends on mode:

- `Full image`: the repair removes an edge-connected background artifact after the binary mask is produced and then re-runs measurement on the corrected mask.
- `Thumbnails`: the workflow first runs a lightweight preflight on the source image. If strong dark-edge artifacts are detected, it switches to the stable repair path; otherwise it stays on the original FAMeLeS thumbnails macro path.

When summarizing a run for the user:

- check `run_summary.md` for whether repair was triggered
- check `method_summary.md` for whether the run stayed on the original path or used the repair path
- if `results_fameles_particles_raw.csv` exists, explain that it preserves the original Fiji particle-level table while `results.csv` is normalized to one row per exported thumbnail
- remind the user to visually inspect the binary and outline outputs
