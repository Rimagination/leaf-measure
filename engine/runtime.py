from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys

from engine.config import RuntimeConfig, read_runtime_config
from engine.errors import LeafMeasureError


@dataclass(frozen=True)
class ResolvedRuntime:
    repo_root: Path
    fiji_dir: Path
    python_exe: Path
    assets_dir: Path
    display_environment: str
    source: str


@dataclass(frozen=True)
class RuntimeProbe:
    repo_root: Path
    config_path: Path
    fiji_dir: Path | None
    python_exe: Path
    assets_dir: Path | None
    display_environment: str
    source: str
    fiji_candidates: list[Path]
    assets_candidates: list[Path]
    issues: list[str]

    @property
    def ready(self) -> bool:
        return self.fiji_dir is not None and self.assets_dir is not None


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


def probe_runtime(
    *,
    cli_fiji_dir: Path | None = None,
    cli_python_exe: Path | None = None,
    cli_assets_dir: Path | None = None,
    root: Path | None = None,
) -> RuntimeProbe:
    root = repo_root(root)
    config_path = runtime_config_path(root)
    config = read_runtime_config(config_path)
    env_fiji = os.environ.get("FIJI_DIR")
    env_python = os.environ.get("PYTHON_EXE")
    env_assets = os.environ.get("LEAF_MEASURE_ASSETS_DIR")

    fiji_dir: Path | None = None
    python_exe: Path | None = None
    assets_dir: Path | None = None
    source = "local-discovery"
    fiji_candidates = discover_fiji_candidates(root)
    assets_candidates = discover_assets_candidates(root)
    issues: list[str] = []

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
        for candidate in fiji_candidates:
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
        for candidate in assets_candidates:
            if looks_like_assets_root(candidate):
                assets_dir = candidate
                break

    if fiji_dir is None:
        issues.append("missing_fiji")
    if assets_dir is None:
        issues.append("missing_assets")

    return RuntimeProbe(
        repo_root=root,
        config_path=config_path,
        fiji_dir=fiji_dir,
        python_exe=python_exe,
        assets_dir=assets_dir,
        display_environment=detect_display_environment(),
        source=source,
        fiji_candidates=fiji_candidates,
        assets_candidates=assets_candidates,
        issues=issues,
    )


def resolve_runtime(
    *,
    cli_fiji_dir: Path | None = None,
    cli_python_exe: Path | None = None,
    cli_assets_dir: Path | None = None,
    root: Path | None = None,
) -> ResolvedRuntime:
    probe = probe_runtime(
        cli_fiji_dir=cli_fiji_dir,
        cli_python_exe=cli_python_exe,
        cli_assets_dir=cli_assets_dir,
        root=root,
    )
    if probe.fiji_dir is None:
        raise LeafMeasureError(
            code="missing_fiji",
            message="Could not resolve Fiji.",
            hints=[
                "Run `python -m engine.cli fetch-fiji` or `./scripts/bootstrap.ps1`.",
                "Or provide `--fiji`, set `config/runtime.toml`, or set `FIJI_DIR`.",
            ],
            details={
                "config_path": probe.config_path,
                "fiji_candidates": probe.fiji_candidates,
            },
        )
    if probe.assets_dir is None:
        raise LeafMeasureError(
            code="missing_assets",
            message="Could not resolve leaf-measure assets.",
            hints=[
                "Run `python -m engine.cli fetch-assets` or `./scripts/bootstrap.ps1`.",
                "Or provide `--assets`, set `config/runtime.toml`, or set `LEAF_MEASURE_ASSETS_DIR`.",
            ],
            details={
                "config_path": probe.config_path,
                "assets_candidates": probe.assets_candidates,
            },
        )

    return ResolvedRuntime(
        repo_root=probe.repo_root,
        fiji_dir=probe.fiji_dir,
        python_exe=probe.python_exe,
        assets_dir=probe.assets_dir,
        display_environment=probe.display_environment,
        source=probe.source,
    )
