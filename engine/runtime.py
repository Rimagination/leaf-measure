from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys

from engine.config import RuntimeConfig, read_runtime_config
from engine.errors import LeafMeasureError
from engine.fiji import (
    discover_fiji_from_path,
    discover_local_and_common_fiji_candidates,
    load_cached_fiji,
    remember_fiji_installation,
    resolve_fiji_installation,
    runtime_cache_path,
)


@dataclass(frozen=True)
class ResolvedRuntime:
    repo_root: Path
    fiji_dir: Path
    fiji_launcher: Path
    python_exe: Path
    assets_dir: Path
    display_environment: str
    source: str


@dataclass(frozen=True)
class RuntimeProbe:
    repo_root: Path
    config_path: Path
    cache_path: Path
    fiji_dir: Path | None
    fiji_launcher: Path | None
    python_exe: Path
    assets_dir: Path | None
    display_environment: str
    source: str
    fiji_candidates: list[Path]
    assets_candidates: list[Path]
    issues: list[str]

    @property
    def ready(self) -> bool:
        return self.fiji_launcher is not None and self.assets_dir is not None


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


def valid_python_exe(path: Path | None) -> Path | None:
    if path is None:
        return None
    resolved = path.resolve()
    return resolved if resolved.exists() else None


def valid_assets_dir(path: Path | None) -> Path | None:
    if path is None:
        return None
    resolved = path.resolve()
    return resolved if looks_like_assets_root(resolved) else None


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
    fiji_launcher: Path | None = None
    python_exe: Path | None = None
    assets_dir: Path | None = None
    source = "local-discovery"
    cache_path = runtime_cache_path(root)
    fiji_candidates: list[Path] = []
    assets_candidates = discover_assets_candidates(root)
    issues: list[str] = []
    explicit_fiji_requested = cli_fiji_dir is not None
    explicit_assets_requested = cli_assets_dir is not None

    if cli_fiji_dir:
        fiji_candidates.append(cli_fiji_dir.resolve())
        resolved_fiji = resolve_fiji_installation(cli_fiji_dir)
        if resolved_fiji is not None:
            fiji_dir = resolved_fiji.root_dir
            fiji_launcher = resolved_fiji.launcher
            source = "cli"
    if fiji_launcher is None and not explicit_fiji_requested and env_fiji:
        env_fiji_path = Path(env_fiji)
        fiji_candidates.append(env_fiji_path.resolve())
        resolved_fiji = resolve_fiji_installation(env_fiji_path)
        if resolved_fiji is not None:
            fiji_dir = resolved_fiji.root_dir
            fiji_launcher = resolved_fiji.launcher
            source = "env"
    if fiji_launcher is None and not explicit_fiji_requested and config.fiji_dir:
        config_fiji_path = config.fiji_dir.resolve()
        fiji_candidates.append(config_fiji_path)
        resolved_fiji = resolve_fiji_installation(config.fiji_dir)
        if resolved_fiji is not None:
            fiji_dir = resolved_fiji.root_dir
            fiji_launcher = resolved_fiji.launcher
            source = "config"

    if fiji_launcher is None and not explicit_fiji_requested:
        resolved_from_path, path_candidates = discover_fiji_from_path()
        fiji_candidates.extend(path_candidates)
        if resolved_from_path is not None:
            fiji_dir = resolved_from_path.root_dir
            fiji_launcher = resolved_from_path.launcher
            source = "path"

    if fiji_launcher is None and not explicit_fiji_requested:
        local_candidates = discover_local_and_common_fiji_candidates(root)
        fiji_candidates.extend(local_candidates)
        for candidate in local_candidates:
            resolved_fiji = resolve_fiji_installation(candidate)
            if resolved_fiji is None:
                continue
            fiji_dir = resolved_fiji.root_dir
            fiji_launcher = resolved_fiji.launcher
            source = "local-discovery"
            break

    if fiji_launcher is None and not explicit_fiji_requested:
        cached_fiji = load_cached_fiji(root)
        if cached_fiji is not None:
            fiji_dir = cached_fiji.root_dir
            fiji_launcher = cached_fiji.launcher
            source = "cache"

    if cli_python_exe:
        python_exe = cli_python_exe.resolve()
    elif valid_python_exe(config.python_exe):
        python_exe = valid_python_exe(config.python_exe)
    elif env_python:
        python_exe = valid_python_exe(Path(env_python)) or Path(sys.executable).resolve()
    else:
        python_exe = Path(sys.executable).resolve()

    if cli_assets_dir:
        assets_dir = valid_assets_dir(cli_assets_dir)
    if assets_dir is None and not explicit_assets_requested and env_assets:
        assets_dir = valid_assets_dir(Path(env_assets))
    if assets_dir is None and not explicit_assets_requested and valid_assets_dir(config.assets_dir):
        assets_dir = valid_assets_dir(config.assets_dir)
    if assets_dir is None and not explicit_assets_requested:
        for candidate in assets_candidates:
            if looks_like_assets_root(candidate):
                assets_dir = candidate
                break

    if fiji_launcher is None:
        issues.append("missing_fiji")
    if assets_dir is None:
        issues.append("missing_assets")

    if fiji_launcher is not None:
        resolved_for_cache = resolve_fiji_installation(fiji_launcher)
        if resolved_for_cache is not None:
            remember_fiji_installation(root, resolved_for_cache)

    return RuntimeProbe(
        repo_root=root,
        config_path=config_path,
        cache_path=cache_path,
        fiji_dir=fiji_dir,
        fiji_launcher=fiji_launcher,
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
    if probe.fiji_launcher is None:
        raise LeafMeasureError(
            stage="runtime_discovery",
            code="missing_fiji",
            message="Could not resolve Fiji.",
            hints=[
                "Run `python -m engine.cli fetch-fiji` or `./scripts/bootstrap.ps1`.",
                "Or provide `--fiji` as a Fiji directory or launcher path, set `config/runtime.toml`, or set `FIJI_DIR`.",
            ],
            details={
                "config_path": probe.config_path,
                "cache_path": probe.cache_path,
                "fiji_candidates": probe.fiji_candidates,
            },
        )
    if probe.assets_dir is None:
        raise LeafMeasureError(
            stage="runtime_discovery",
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
        fiji_launcher=probe.fiji_launcher,
        python_exe=probe.python_exe,
        assets_dir=probe.assets_dir,
        display_environment=probe.display_environment,
        source=probe.source,
    )
