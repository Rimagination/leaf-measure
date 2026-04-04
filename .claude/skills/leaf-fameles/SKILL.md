---
name: leaf-fameles
description: Use when measuring leaf area, perimeter, length, width, circularity, and solidity from a folder of leaf images with the Fiji-based FAMeLeS workflow, especially when the user asks to analyze a directory of leaf scans or photos and needs a results table plus segmentation outputs.
---

# leaf-fameles

Use this skill to run the shared `leaf-measure` engine, not to re-implement the method in the prompt.

This skill supports two host patterns:

- repo-local: the current workspace is the `leaf-measure` repository
- standalone installed skill: the skill lives under `$CODEX_HOME/skills/leaf-fameles` and uses `scripts/setup_and_analyze.py` to clone or update the shared repo cache under `$CODEX_HOME/vendor/leaf-measure`

## Workflow

1. Confirm the target image folder.
2. If the user did not specify a mode, explain `Full image` vs `Thumbnails` using `references/mode-selection.md` and ask them to choose.
3. Before analysis, make sure the runtime exists:
   - repo-local: prefer `.\scripts\bootstrap.ps1` on Windows because it installs the current Python dependencies, downloads Fiji if missing, and fetches the public Figshare assets if missing
   - standalone installed skill: run `python scripts/setup_and_analyze.py analyze ...`; that helper clones or updates the shared repo cache, runs `doctor`, and bootstraps the runtime on first use when needed
   - if only the upstream package is missing in a repo-local workspace, run `python -m engine.cli fetch-assets`
4. Run the shared CLI from the repository root:

```powershell
python -m engine.cli analyze --input "<folder>" --output "<run-dir>" --mode full
```

or

```powershell
python -m engine.cli analyze --input "<folder>" --output "<run-dir>" --mode thumbnails
```

For a standalone installed skill, use the bundled helper instead of assuming the current directory is the repo:

```powershell
python scripts/setup_and_analyze.py analyze --input "<folder>" --output "<run-dir>" --mode full
```

or

```powershell
python scripts/setup_and_analyze.py analyze --input "<folder>" --output "<run-dir>" --mode thumbnails
```

5. Read `manifest.json`, `results.csv`, `run_summary.md`, and the output folders before answering.
6. Explain:
   - what was measured
   - which mode was used
   - that `results.csv` is the user-facing table and `results_fameles_particles_raw.csv` preserves the original particle-level table when present
   - that outputs are in pixels by default
   - whether DPI metadata was found
   - whether automatic repair was triggered for a mask artifact
   - that binary and outline outputs should be visually reviewed

## References

- Mode choice: `references/mode-selection.md`
- Trait definitions: `references/trait-definitions.md`
- Artifact handling: `references/artifact-handling.md`

## Boundaries

- Do not silently convert pixel outputs into physical units.
- Do not claim the method worked if `results.csv` or output images are missing.
- Treat the shared CLI as the source of truth.
- If the standalone helper cannot make the runtime ready, surface the bootstrap or doctor failure clearly instead of improvising.
