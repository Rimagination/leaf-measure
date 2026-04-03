from __future__ import annotations

import argparse
from pathlib import Path

from engine.dpi import collect_dpi_metadata
from engine.executors import run_batch_macro
from engine.macros import build_full_macro, build_thumbnails_macro, original_macro
from engine.reporting import (
    normalize_results_csv,
    write_manifest,
    write_method_summary,
    write_run_summary,
    write_trait_explanations,
)
from engine.runtime import resolve_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run leaf-measure analyses.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze a folder of leaf images.")
    analyze.add_argument("--input", type=Path, required=True)
    analyze.add_argument("--output", type=Path, required=True)
    analyze.add_argument("--mode", choices=["full", "thumbnails"], required=True)
    analyze.add_argument("--fiji", type=Path)
    analyze.add_argument("--python", type=Path, dest="python_exe")
    analyze.add_argument("--assets", type=Path, dest="assets_dir")
    return parser.parse_args()


def supported_input_files(input_dir: Path) -> list[Path]:
    supported = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
    return [
        path
        for path in sorted(input_dir.iterdir())
        if path.is_file() and not path.name.startswith(".") and path.suffix.lower() in supported
    ]


def build_outputs(output_dir: Path, mode: str) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = output_dir / "_work"
    work_dir.mkdir(exist_ok=True)
    if mode == "full":
        paths = {
            "bandpass": output_dir / "01b_bandpass",
            "contrasted": output_dir / "01c_contrasted",
            "area": output_dir / "02_area",
            "outline": output_dir / "03_outline",
            "work": work_dir,
        }
    else:
        paths = {
            "bandpass": output_dir / "01a_bandpass",
            "contrasted": output_dir / "01b_contrasted",
            "thumbnails": output_dir / "02_thumbnails",
            "area": output_dir / "03_area",
            "outline": output_dir / "04_outline",
            "work": work_dir,
        }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def analyze(args: argparse.Namespace) -> int:
    runtime = resolve_runtime(
        cli_fiji_dir=args.fiji,
        cli_python_exe=args.python_exe,
        cli_assets_dir=args.assets_dir,
    )
    input_files = supported_input_files(args.input)
    if not input_files:
        raise FileNotFoundError(f"No supported images found in {args.input}")

    outputs = build_outputs(args.output, args.mode)
    results_csv = args.output / "results.csv"
    warnings: list[str] = []

    if args.mode == "full":
        macro = build_full_macro(
            template_path=original_macro(runtime.assets_dir, "full"),
            input_dir=args.input,
            bandpass_dir=outputs["bandpass"],
            contrasted_dir=outputs["contrasted"],
            area_dir=outputs["area"],
            outline_dir=outputs["outline"],
            results_csv=results_csv,
        )
    else:
        macro = build_thumbnails_macro(
            template_path=original_macro(runtime.assets_dir, "thumbnails"),
            input_dir=args.input,
            bandpass_dir=outputs["bandpass"],
            contrasted_dir=outputs["contrasted"],
            thumbnails_dir=outputs["thumbnails"],
            area_dir=outputs["area"],
            outline_dir=outputs["outline"],
            results_csv=results_csv,
        )

    execution = run_batch_macro(
        fiji_dir=runtime.fiji_dir,
        macro_text=macro,
        work_dir=outputs["work"],
    )
    if execution.exit_code != 0:
        warnings.append(f"Fiji returned exit code {execution.exit_code}. Check run logs in _work/.")
    if not results_csv.exists():
        raise RuntimeError(
            f"Fiji run did not produce {results_csv}. See {execution.stderr_log} for details."
        )

    normalize_results_csv(results_csv)
    dpi_metadata = collect_dpi_metadata(args.input)
    if all(value is None for value in dpi_metadata.values()):
        warnings.append("No DPI metadata was found; results remain in pixels.")

    write_method_summary(
        args.output / "method_summary.md",
        mode=args.mode,
        executor=execution.executor,
    )
    write_trait_explanations(args.output / "trait_explanations.md")
    write_run_summary(
        args.output / "run_summary.md",
        mode=args.mode,
        executor=execution.executor,
        image_count=len(input_files),
        dpi_metadata=dpi_metadata,
        warnings=warnings,
    )
    write_manifest(
        args.output / "manifest.json",
        {
            "mode": args.mode,
            "executor": execution.executor,
            "runtime_source": runtime.source,
            "display_environment": runtime.display_environment,
            "fiji_dir": runtime.fiji_dir,
            "assets_dir": runtime.assets_dir,
            "results_csv": results_csv,
            "stdout_log": execution.stdout_log,
            "stderr_log": execution.stderr_log,
            "image_count": len(input_files),
            "dpi_metadata": dpi_metadata,
            "warnings": warnings,
        },
    )
    print(results_csv)
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "analyze":
        return analyze(args)
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
