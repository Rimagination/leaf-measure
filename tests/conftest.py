from __future__ import annotations

import csv
import hashlib
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def local_fiji_dir() -> Path:
    candidates = [
        Path(r"D:\VSP\leaf\fiji-latest-win64-jdk\Fiji"),
        Path(r"D:\VSP\fiji-latest-win64-jdk\Fiji"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    pytest.skip("Local Fiji installation not found for integration tests.")


@pytest.fixture(scope="session")
def available_assets_dir(repo_root: Path) -> Path:
    candidates = [
        repo_root / ".leaf-measure-assets",
        repo_root,
        Path(r"D:\VSP\leaf"),
    ]
    for candidate in candidates:
        if (
            (candidate / "macros" / "original" / "Fameles_v2_Full_image.ijm").exists()
            and (candidate / "fixtures" / "trial_input").exists()
        ):
            return candidate
    pytest.skip("No leaf-measure assets root available for integration tests.")


@pytest.fixture(scope="session")
def validation_assets_dir(repo_root: Path) -> Path:
    candidates = [
        repo_root / ".leaf-measure-assets",
        repo_root,
    ]
    for candidate in candidates:
        if (
            (candidate / "macros" / "original" / "Fameles_v2_Full_image.ijm").exists()
            and (candidate / "fixtures" / "trial_input").exists()
            and (candidate / "golden" / "full_image" / "results_full.csv").exists()
        ):
            return candidate
    pytest.skip("No validation assets root available for integration tests.")


def normalized_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    return [
        {key: value for key, value in row.items() if key and key.strip()}
        for row in rows
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_cli(
    *,
    repo_root: Path,
    input_dir: Path,
    output_dir: Path,
    mode: str,
    fiji_dir: Path,
    assets_dir: Path | None = None,
):
    cmd = [
        sys.executable,
        "-m",
        "engine.cli",
        "analyze",
        "--input",
        str(input_dir),
        "--output",
        str(output_dir),
        "--mode",
        mode,
        "--fiji",
        str(fiji_dir),
    ]
    if assets_dir is not None:
        cmd.extend(["--assets", str(assets_dir)])
    return subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
