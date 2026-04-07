# Artifact Handling

`leaf-measure` keeps the published FAMeLeS path by default.

If the machine is missing upstream macros or Fiji, prefer `.\scripts\bootstrap.ps1` first. It installs the current Python dependencies and fetches missing public runtime assets before analysis.

Automatic repair depends on mode:

- `Full image`: the repair keeps the published macro path first. If the saved binary mask is hole-dominated, `leaf-measure` fixes the measurement polarity for the user-facing table. In sparse edge cases it may compare both polarities against the source image to choose the foreground interpretation that better matches darker leaf material. If that repaired mask still appears to miss large leaf objects, `leaf-measure` reruns the original `Full image` macro on a small number of candidate crop regions and only merges newly recovered, non-edge-touching foreground objects before the final user-facing measurement pass.
- `Thumbnails`: the workflow first runs a lightweight preflight on the source image. If strong dark-edge artifacts are detected, it switches to the stable repair path; otherwise it stays on the original FAMeLeS thumbnails macro path.

When summarizing a run for the user:

- check `run_summary.md` for whether repair was triggered
- check `method_summary.md` for whether the run stayed on the original path or used the repair path
- if `results_fameles_particles_raw.csv` exists, explain that it preserves the original Fiji particle-level table while `results.csv` is the cleaned user-facing table
- if the run used non-ASCII filenames, mention that leaf-measure staged them internally to ASCII-safe temporary names and restored the original names in the delivered outputs
- remind the user to visually inspect the binary and outline outputs
