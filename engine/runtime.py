from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys

from engine.config import RuntimeConfig, read_runtime_config


@dataclass(frozen=True)
class ResolvedRuntime:
    repo_root: Path
    fiji_dir: Path
    python_exe: Path
    assets_dir: Path
    display_environment: str
    source: str


def repo_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__).resolve()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError("Could not locate repository root from pyproject.toml")


def runtime_config_path(root: Path) -> Path:
    return root / "config" / "runtime.toml"


def detect_display_environment() -> str:
    if sys.platform.startswith("win"):
        return "windows-desktop"
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return "gui-display"
    if os.environ.get("XVFB_RUN") or os.environ.get("CI_XVFB"):
        return "virtual-display"
    return "headless-or-unknown"


def discover_fiji_candidates(root: Path) -> list[Path]:
    candidates = [
        root / "fiji-latest-win64-jdk" / "Fiji",
        root / "Fiji",
        root.parent / "fiji-latest-win64-jdk" / "Fiji",
        root.parent / "leaf" / "fiji-latest-win64-jdk" / "Fiji",
    ]
    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped


def discover_assets_candidates(root: Path) -> list[Path]:
    candidates = [
        root / ".leaf-measure-assets",
        root,
        root.parent / "leaf-measure-assets",
        root.parent / "leaf",
    ]
    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped


def looks_like_assets_root(path: Path) -> bool:
    checks = [
        path / "macros" / "original" / "Fameles_v2_Full_image.ijm",
        path / "macros" / "original" / "Fameles_v2_Thumbnails.ijm",
    ]
    return all(check.exists() for check in checks)


def resolve_runtime(
    *,
    cli_fiji_dir: Path | None = None,
    cli_python_exe: Path | None = None,
    cli_assets_dir: Path | None = None,
    root: Path | None = None,
) -> ResolvedRuntime:
    root = repo_root(root)
    config = read_runtime_config(runtime_config_path(root))
    env_fiji = os.environ.get("FIJI_DIR")
    env_python = os.environ.get("PYTHON_EXE")
    env_assets = os.environ.get("LEAF_MEASURE_ASSETS_DIR")

    fiji_dir: Path | None = None
    python_exe: Path | None = None
    assets_dir: Path | None = None
    source = "local-discovery"

    if cli_fiji_dir:
        fiji_dir = cli_fiji_dir.resolve()
        source = "cli"
    elif config.fiji_dir:
        fiji_dir = config.fiji_dir.resolve()
        source = "config"
    elif env_fiji:
        fiji_dir = Path(env_fiji).resolve()
        source = "env"
    else:
        for candidate in discover_fiji_candidates(root):
            if candidate.exists():
                fiji_dir = candidate
                break

    if cli_python_exe:
        python_exe = cli_python_exe.resolve()
    elif config.python_exe:
        python_exe = config.python_exe.resolve()
    elif env_python:
        python_exe = Path(env_python).resolve()
    else:
        python_exe = Path(sys.executable).resolve()

    if cli_assets_dir:
        assets_dir = cli_assets_dir.resolve()
    elif config.assets_dir:
        assets_dir = config.assets_dir.resolve()
    elif env_assets:
        assets_dir = Path(env_assets).resolve()
    else:
        for candidate in discover_assets_candidates(root):
            if looks_like_assets_root(candidate):
                assets_dir = candidate
                break

    if fiji_dir is None:
        raise FileNotFoundError(
            "Could not resolve Fiji. Provide --fiji, set config/runtime.toml, "
            "or set FIJI_DIR."
        )
    if assets_dir is None:
        raise FileNotFoundError(
            "Could not resolve leaf-measure assets. Provide --assets, set "
            "config/runtime.toml, set LEAF_MEASURE_ASSETS_DIR, or stage upstream assets "
            "into .leaf-measure-assets/. You can also run "
            "`python -m engine.cli fetch-assets` to download the public Figshare package."
        )

    return ResolvedRuntime(
        repo_root=root,
        fiji_dir=fiji_dir,
        python_exe=python_exe,
        assets_dir=assets_dir,
        display_environment=detect_display_environment(),
        source=source,
    )
