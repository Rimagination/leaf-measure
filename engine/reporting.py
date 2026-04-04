from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


TRAIT_DEFINITIONS = {
    "Area": "Projected leaf area measured from the binary segmentation.",
    "Perim.": "Leaf perimeter measured from the segmented object boundary.",
    "Length": "Leaf length derived from the Feret diameter reported by Fiji.",
    "Width ": "Leaf width derived from the minimum Feret diameter reported by Fiji.",
    "Circ.": "Circularity computed by Fiji from area and perimeter.",
    "Solidity": "Solidity computed as area divided by convex area.",
}


def normalize_results_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    drop_columns = [
        column
        for column in frame.columns
        if column.startswith("Unnamed:") or not str(column).strip()
    ]
    if "Mean" in frame.columns:
        drop_columns.append("Mean")
    if drop_columns:
        frame = frame.drop(columns=drop_columns)
    if "Label" in frame.columns:
        frame["Label"] = frame["Label"].fillna("").astype(str)
        frame = frame[frame["Label"].str.strip() != ""].reset_index(drop=True)
    frame.to_csv(path, index=False)
    return frame


def write_method_summary(path: Path, *, mode: str, executor: str, repair_note: str | None = None) -> None:
    text = (
        "# Method Summary\n\n"
        "This run executed the Fiji-based FAMeLeS workflow through the leaf-measure engine.\n\n"
        f"- Mode: `{mode}`\n"
        f"- Executor: `{executor}`\n"
        "- Default unit: pixels\n"
        "- Physical-unit conversion is not applied automatically\n"
    )
    if repair_note:
        text += f"- Repair behavior: {repair_note}\n"
    path.write_text(text, encoding="utf-8")


def write_trait_explanations(path: Path) -> None:
    lines = ["# Trait Explanations", ""]
    for name, definition in TRAIT_DEFINITIONS.items():
        lines.append(f"- `{name}`: {definition}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_run_summary(
    path: Path,
    *,
    mode: str,
    executor: str,
    image_count: int,
    dpi_metadata: dict[str, tuple[float, float] | None],
    warnings: list[str],
) -> None:
    lines = [
        "# Run Summary",
        "",
        f"- Mode: `{mode}`",
        f"- Executor: `{executor}`",
        f"- Image count: `{image_count}`",
        "- Unit note: measurements are reported in pixels by default",
    ]
    if any(value is not None for value in dpi_metadata.values()):
        lines.append("- DPI metadata: found for at least one image")
    else:
        lines.append("- DPI metadata: not found")
    if warnings:
        lines.append("- Warnings:")
        for warning in warnings:
            lines.append(f"  - {warning}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, payload: dict) -> None:
    def default(value: object):
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, tuple):
            return list(value)
        raise TypeError(f"Unsupported manifest value: {value!r}")

    path.write_text(json.dumps(payload, indent=2, default=default), encoding="utf-8")
