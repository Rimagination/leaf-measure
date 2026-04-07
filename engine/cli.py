from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
import sys

from engine.dpi import collect_dpi_metadata
from engine.errors import LeafMeasureError, write_failure_report
from engine.executors import run_batch_macro
from engine.macros import (
    build_full_macro,
    build_full_measurement_macro,
    build_thumbnail_outline_macro,
    build_thumbnails_macro,
    build_thumbnail_measurement_macro,
    original_macro,
)
from engine.mask_correction import correct_full_masks
from engine.preprocess import (
    restore_output_filenames,
    restore_staged_name,
    should_prefer_thumbnail_repair,
    stage_input_images,
)
from engine.thumbnail_extraction import extract_thumbnails_from_masks
from engine.thumbnail_measurements import write_thumbnail_results_csv
from engine.reporting import (
    filter_full_image_results,
    remap_results_labels,
    normalize_results_csv,
    write_manifest,
    write_method_summary,
    write_run_summary,
    write_trait_explanations,
)
from engine.runtime import probe_runtime, repo_root, resolve_runtime
from engine.sanity import full_image_sanity_warnings, image_area_map
from engine.skill_sync import default_skill_install_root, install_skill, sync_all_skills
from engine.upstream import download_and_extract_fiji, download_and_stage_figshare_assets


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

    doctor = subparsers.add_parser(
        "doctor",
        help="Probe runtime readiness and write a machine-readable environment report.",
    )
    doctor.add_argument("--fiji", type=Path)
    doctor.add_argument("--python", type=Path, dest="python_exe")
    doctor.add_argument("--assets", type=Path, dest="assets_dir")
    doctor.add_argument("--output", type=Path)
    doctor.add_argument("--json", action="store_true", dest="emit_json")

    fetch_assets = subparsers.add_parser(
        "fetch-assets",
        help="Download the upstream FAMeLeS macros and trial package from Figshare.",
    )
    fetch_assets.add_argument("--destination", type=Path)
    fetch_assets.add_argument("--article-id", default="22354405")

    fetch_fiji = subparsers.add_parser(
        "fetch-fiji",
        help="Download the latest Fiji distribution into a local runtime directory.",
    )
    fetch_fiji.add_argument("--destination", type=Path)

    sync_skills = subparsers.add_parser(
        "sync-skills",
        help="Sync canonical skills/ into repo-local .agents/ and .claude/ skill directories.",
    )
    sync_skills.add_argument("--repo-root", type=Path)

    install_skill_parser = subparsers.add_parser(
        "install-skill",
        help="Install the canonical leaf-measure skill into a target global skill directory.",
    )
    install_skill_parser.add_argument("--repo-root", type=Path)
    install_skill_parser.add_argument("--skill-name", default="leaf-measure")
    install_skill_parser.add_argument("--destination", type=Path)
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


def clear_directory(path: Path) -> None:
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def copy_files(source_dir: Path, dest_dir: Path) -> None:
    clear_directory(dest_dir)
    for path in sorted(source_dir.iterdir()):
        if path.is_file():
            shutil.copy2(path, dest_dir / path.name)


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
    staged_input = stage_input_images(args.input, outputs["work"] / "input_staged")
    results_csv = args.output / "results.csv"
    raw_results_csv = args.output / "results_fameles_particles_raw.csv"
    initial_results_csv = results_csv
    warnings: list[str] = []
    repair_note = "none"
    if staged_input.modified_files:
        warnings.append(
            f"Removed dark edge artifacts from {len(staged_input.modified_files)} input image(s) before Fiji execution."
        )

    if args.mode == "full":
        initial_results_csv = raw_results_csv
        macro = build_full_macro(
            template_path=original_macro(runtime.assets_dir, "full"),
            input_dir=staged_input.staged_dir,
            bandpass_dir=outputs["bandpass"],
            contrasted_dir=outputs["contrasted"],
            area_dir=outputs["area"],
            outline_dir=outputs["outline"],
            results_csv=raw_results_csv,
        )
    elif should_prefer_thumbnail_repair(staged_input):
        probe_bandpass = outputs["work"] / "probe_bandpass"
        probe_contrasted = outputs["work"] / "probe_contrasted"
        temp_full_area = outputs["work"] / "full_area"
        temp_full_outline = outputs["work"] / "full_outline"
        probe_bandpass.mkdir(parents=True, exist_ok=True)
        probe_contrasted.mkdir(parents=True, exist_ok=True)
        temp_full_area.mkdir(parents=True, exist_ok=True)
        temp_full_outline.mkdir(parents=True, exist_ok=True)
        temp_full_results = outputs["work"] / "full_results.csv"
        initial_results_csv = temp_full_results
        macro = build_full_macro(
            template_path=original_macro(runtime.assets_dir, "full"),
            input_dir=staged_input.staged_dir,
            bandpass_dir=probe_bandpass,
            contrasted_dir=probe_contrasted,
            area_dir=temp_full_area,
            outline_dir=temp_full_outline,
            results_csv=temp_full_results,
        )
    else:
        macro = build_thumbnails_macro(
            template_path=original_macro(runtime.assets_dir, "thumbnails"),
            input_dir=staged_input.staged_dir,
            bandpass_dir=outputs["bandpass"],
            contrasted_dir=outputs["contrasted"],
            thumbnails_dir=outputs["thumbnails"],
            area_dir=outputs["area"],
            outline_dir=outputs["outline"],
            results_csv=raw_results_csv,
        )
        initial_results_csv = raw_results_csv

    execution = run_batch_macro(
        fiji_path=runtime.fiji_launcher,
        macro_text=macro,
        work_dir=outputs["work"],
    )
    if execution.exit_code != 0:
        warnings.append(f"Fiji returned exit code {execution.exit_code}. Check run logs in _work/.")
    if not initial_results_csv.exists():
        raise LeafMeasureError(
            stage="results_read",
            code="missing_results_csv",
            message=f"Fiji did not produce the expected results table: {initial_results_csv.name}.",
            hints=[
                "Inspect `failure.json` and the Fiji logs under `_work/`.",
                "If stdout/stderr are empty, verify Fiji launched correctly and rerun `python -m engine.cli doctor`.",
            ],
            details={
                "expected_results_csv": initial_results_csv,
                "stdout_log": execution.stdout_log,
                "stderr_log": execution.stderr_log,
                "executor": execution.executor,
                "fiji_exit_code": execution.exit_code,
            },
        )

    normalize_results_csv(initial_results_csv)
    corrected_mask_files: list[str] = []
    if args.mode == "full":
        correction = correct_full_masks(outputs["area"])
        corrected_mask_files = correction.corrected_files
        if corrected_mask_files:
            warnings.append(
                f"Corrected {len(corrected_mask_files)} binary mask(s) by removing edge-connected background regions before measurement."
            )
            rerun = run_batch_macro(
                fiji_path=runtime.fiji_launcher,
                macro_text=build_full_measurement_macro(
                    area_dir=outputs["area"],
                    outline_dir=outputs["outline"],
                    results_csv=raw_results_csv,
                ),
                work_dir=outputs["work"] / "measurement_rerun",
            )
            execution = rerun
            if rerun.exit_code != 0:
                warnings.append(
                    f"Fiji returned exit code {rerun.exit_code} during corrected-mask measurement rerun."
                )
            normalize_results_csv(raw_results_csv)
        full_raw_frame = normalize_results_csv(raw_results_csv)
        full_frame, filter_report = filter_full_image_results(full_raw_frame, area_dir=outputs["area"])
        full_frame.to_csv(results_csv, index=False)
        if filter_report.dropped_rows:
            warnings.append(
                f"Removed {len(filter_report.dropped_rows)} edge-connected background particle row(s) from the user-facing full-image results table. The unfiltered Fiji output is preserved in results_fameles_particles_raw.csv."
            )
        warning_frame = full_frame.copy()
        if staged_input.filename_map and "Label" in warning_frame.columns:
            warning_frame["Label"] = warning_frame["Label"].map(
                lambda value: restore_staged_name(str(value), staged_input.filename_map)
            )
        warnings.extend(
            full_image_sanity_warnings(
                warning_frame,
                image_areas=image_area_map(args.input),
            )
        )
    elif should_prefer_thumbnail_repair(staged_input):
        correction = correct_full_masks(temp_full_area)
        corrected_mask_files = correction.corrected_files
        repair_note = (
            "Thumbnail repair was enabled after a lightweight preflight detected dark edge artifacts in the source image. "
            "leaf-measure used the stable per-leaf export path instead of the original FAMeLeS thumbnails macro path."
        )
        if corrected_mask_files:
            warnings.append(
                f"Applied thumbnail repair to {len(corrected_mask_files)} image(s) after detecting an edge-connected background artifact in the binary mask."
            )
        copy_files(probe_bandpass, outputs["bandpass"])
        copy_files(probe_contrasted, outputs["contrasted"])
        extraction = extract_thumbnails_from_masks(
            full_mask_dir=temp_full_area,
            source_image_dir=staged_input.staged_dir,
            thumbnails_dir=outputs["thumbnails"],
            area_dir=outputs["area"],
        )
        if not extraction.exported_files:
            raise LeafMeasureError(
                stage="result_cleanup",
                code="thumbnail_extraction_empty",
                message="Thumbnail repair path did not produce any per-leaf outputs.",
                hints=[
                    "Review the corrected full-image masks in `_work/full_area`.",
                    "Check whether the input image contains separable leaf objects after segmentation.",
                ],
                details={
                    "full_mask_dir": temp_full_area,
                    "source_image_dir": staged_input.staged_dir,
                },
            )
        rerun = run_batch_macro(
            fiji_path=runtime.fiji_launcher,
            macro_text=build_thumbnail_measurement_macro(
                area_dir=outputs["area"],
                outline_dir=outputs["outline"],
                results_csv=results_csv,
            ),
            work_dir=outputs["work"] / "thumbnail_measurement_rerun",
        )
        execution = rerun
        if rerun.exit_code != 0:
            warnings.append(
                f"Fiji returned exit code {rerun.exit_code} during thumbnail measurement rerun."
            )
        write_thumbnail_results_csv(area_dir=outputs["area"], results_csv=results_csv)
    else:
        repair_note = (
            "No artifact-triggered repair was needed. The run used the original FAMeLeS thumbnails macro path."
        )
        if not raw_results_csv.exists():
            raise LeafMeasureError(
                stage="results_read",
                code="missing_thumbnail_results_csv",
                message=f"Fiji did not produce the expected thumbnails results table: {raw_results_csv.name}.",
                hints=[
                    "Inspect `failure.json` and the Fiji logs under `_work/`.",
                    "If stdout/stderr are empty, verify Fiji launched correctly and rerun `python -m engine.cli doctor`.",
                ],
                details={
                    "expected_results_csv": raw_results_csv,
                    "stdout_log": execution.stdout_log,
                    "stderr_log": execution.stderr_log,
                    "executor": execution.executor,
                    "fiji_exit_code": execution.exit_code,
                },
            )
        raw_frame = normalize_results_csv(raw_results_csv)
        rerun_outline = run_batch_macro(
            fiji_path=runtime.fiji_launcher,
            macro_text=build_thumbnail_outline_macro(
                area_dir=outputs["area"],
                outline_dir=outputs["outline"],
            ),
            work_dir=outputs["work"] / "thumbnail_outline_rerun",
        )
        execution = rerun_outline
        if rerun_outline.exit_code != 0:
            warnings.append(
                f"Fiji returned exit code {rerun_outline.exit_code} during thumbnail outline regeneration."
            )
        cleaned_frame = write_thumbnail_results_csv(area_dir=outputs["area"], results_csv=results_csv)
        if len(raw_frame) != len(cleaned_frame):
            warnings.append(
                "The original FAMeLeS thumbnails macro measured multiple particles in at least one exported thumbnail. "
                "leaf-measure kept that raw particle-level table in results_fameles_particles_raw.csv and wrote a one-row-per-thumbnail table to results.csv."
            )

    restore_output_filenames(
        [
            outputs["bandpass"],
            outputs["contrasted"],
            outputs["area"],
            outputs["outline"],
            *([outputs["thumbnails"]] if "thumbnails" in outputs else []),
        ],
        staged_input.filename_map,
    )
    remap_results_labels(results_csv, staged_input.filename_map)
    remap_results_labels(raw_results_csv, staged_input.filename_map)
    dpi_metadata = collect_dpi_metadata(args.input)
    if all(value is None for value in dpi_metadata.values()):
        warnings.append("No DPI metadata was found; results remain in pixels.")

    write_method_summary(
        args.output / "method_summary.md",
        mode=args.mode,
        executor=execution.executor,
        repair_note=repair_note if args.mode == "thumbnails" else None,
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
    display_corrected_mask_files = [
        restore_staged_name(name, staged_input.filename_map) for name in corrected_mask_files
    ]

    write_manifest(
        args.output / "manifest.json",
        {
            "mode": args.mode,
            "executor": execution.executor,
            "runtime_source": runtime.source,
            "display_environment": runtime.display_environment,
            "fiji_dir": runtime.fiji_dir,
            "fiji_launcher": runtime.fiji_launcher,
            "assets_dir": runtime.assets_dir,
            "staged_input_dir": staged_input.staged_dir,
            "preprocessing_modified_files": staged_input.modified_files,
            "filename_map": staged_input.filename_map,
            "corrected_mask_files": display_corrected_mask_files,
            "results_csv": results_csv,
            "raw_results_csv": raw_results_csv if raw_results_csv.exists() else None,
            "stdout_log": execution.stdout_log,
            "stderr_log": execution.stderr_log,
            "image_count": len(input_files),
            "dpi_metadata": dpi_metadata,
            "warnings": warnings,
        },
    )
    print(results_csv)
    return 0


def doctor(args: argparse.Namespace) -> int:
    probe = probe_runtime(
        cli_fiji_dir=args.fiji,
        cli_python_exe=args.python_exe,
        cli_assets_dir=args.assets_dir,
    )
    payload = {
        "ok": probe.ready,
        "repo_root": probe.repo_root,
        "config_path": probe.config_path,
        "cache_path": probe.cache_path,
        "runtime_source": probe.source,
        "display_environment": probe.display_environment,
        "python_exe": probe.python_exe,
        "fiji_dir": probe.fiji_dir,
        "fiji_launcher": probe.fiji_launcher,
        "assets_dir": probe.assets_dir,
        "fiji_candidates": probe.fiji_candidates,
        "assets_candidates": probe.assets_candidates,
        "issues": probe.issues,
        "hints": [
            "Run `./scripts/bootstrap.ps1` on Windows for a one-command setup path.",
            "Run `python -m engine.cli fetch-fiji` if Fiji is missing.",
            "Run `python -m engine.cli fetch-assets` if upstream macros/assets are missing.",
        ],
    }
    if args.output:
        write_manifest(args.output, payload)
        print(args.output)
    elif args.emit_json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(f"ok={probe.ready}")
        print(f"python={probe.python_exe}")
        print(f"fiji={probe.fiji_dir or 'missing'}")
        print(f"launcher={probe.fiji_launcher or 'missing'}")
        print(f"assets={probe.assets_dir or 'missing'}")
        if probe.issues:
            print(f"issues={','.join(probe.issues)}")
    return 0 if probe.ready else 2


def _failure_path_for_args(args: argparse.Namespace) -> Path | None:
    output = getattr(args, "output", None)
    if isinstance(output, Path):
        return output / "failure.json"
    return None


def main() -> int:
    args = parse_args()
    try:
        if args.command == "analyze":
            return analyze(args)
        if args.command == "doctor":
            return doctor(args)
        if args.command == "fetch-assets":
            destination = args.destination or (repo_root() / ".leaf-measure-assets")
            staged = download_and_stage_figshare_assets(destination, article_id=args.article_id)
            print(staged)
            return 0
        if args.command == "fetch-fiji":
            repo = Path(__file__).resolve().parents[1]
            destination = args.destination or (repo / "fiji-latest-win64-jdk")
            fiji_dir = download_and_extract_fiji(destination)
            print(fiji_dir)
            return 0
        if args.command == "sync-skills":
            synced = sync_all_skills(args.repo_root or repo_root())
            for path in synced:
                print(path)
            return 0
        if args.command == "install-skill":
            installed = install_skill(
                args.repo_root or repo_root(),
                args.skill_name,
                args.destination or default_skill_install_root(),
            )
            print(installed)
            return 0
        raise ValueError(f"Unsupported command: {args.command}")
    except LeafMeasureError as error:
        failure_path = _failure_path_for_args(args)
        if failure_path is not None:
            write_failure_report(failure_path, error)
            print(failure_path, file=sys.stderr)
        print(f"{error.code}: {error.message}", file=sys.stderr)
        for hint in error.hints:
            print(f"- {hint}", file=sys.stderr)
        return 2
    except FileNotFoundError as error:
        wrapped = LeafMeasureError(
            stage="input_validation",
            code="file_not_found",
            message=str(error),
            hints=["Check the input path and runtime paths in the doctor report."],
        )
        failure_path = _failure_path_for_args(args)
        if failure_path is not None:
            write_failure_report(failure_path, wrapped)
            print(failure_path, file=sys.stderr)
        print(f"{wrapped.code}: {wrapped.message}", file=sys.stderr)
        return 2
    except RuntimeError as error:
        wrapped = LeafMeasureError(
            stage="analysis_execution",
            code="analysis_failed",
            message=str(error),
            hints=[
                "Inspect `failure.json`, `manifest.json`, and Fiji logs under `_work/`.",
                "Run `python -m engine.cli doctor --output <path>` to capture runtime state.",
            ],
        )
        failure_path = _failure_path_for_args(args)
        if failure_path is not None:
            write_failure_report(failure_path, wrapped)
            print(failure_path, file=sys.stderr)
        print(f"{wrapped.code}: {wrapped.message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
