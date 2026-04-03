---
name: leaf-fameles
description: Use when measuring leaf area, perimeter, length, width, circularity, and solidity from a folder of leaf images with the Fiji-based FAMeLeS workflow, especially when the user asks to analyze a directory of leaf scans or photos and needs a results table plus segmentation outputs.
---

# leaf-fameles

Use this skill to run the shared `leaf-measure` engine, not to re-implement the method in the prompt.

## Workflow

1. Confirm the target image folder.
2. If the user did not specify a mode, explain `Full image` vs `Thumbnails` using `references/mode-selection.md` and ask them to choose.
3. Run the shared CLI from the repository root:

```powershell
python -m engine.cli analyze --input "<folder>" --output "<run-dir>" --mode full
```

or

```powershell
python -m engine.cli analyze --input "<folder>" --output "<run-dir>" --mode thumbnails
```

4. Read `manifest.json`, `results.csv`, `run_summary.md`, and the output folders before answering.
5. Explain:
   - what was measured
   - which mode was used
   - that outputs are in pixels by default
   - whether DPI metadata was found
   - that binary and outline outputs should be visually reviewed

## References

- Mode choice: `references/mode-selection.md`
- Trait definitions: `references/trait-definitions.md`

## Boundaries

- Do not silently convert pixel outputs into physical units.
- Do not claim the method worked if `results.csv` or output images are missing.
- Treat the shared CLI as the source of truth.

