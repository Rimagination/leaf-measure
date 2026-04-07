from __future__ import annotations

import json
from pathlib import Path

from engine.fiji import resolve_fiji_installation
from engine.runtime import resolve_runtime, runtime_cache_path


def _init_repo(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='tmp'\n", encoding="utf-8")
    (tmp_path / "config").mkdir()


def _init_assets(tmp_path: Path) -> Path:
    assets_root = tmp_path / ".leaf-measure-assets"
    macros = assets_root / "macros" / "original"
    macros.mkdir(parents=True)
    (macros / "Fameles_v2_Full_image.ijm").write_text("", encoding="utf-8")
    (macros / "Fameles_v2_Thumbnails.ijm").write_text("", encoding="utf-8")
    return assets_root


def _init_launcher(parent: Path, name: str) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    launcher = parent / name
    launcher.write_text("", encoding="utf-8")
    return launcher


def test_resolve_fiji_installation_accepts_launcher_paths(tmp_path: Path) -> None:
    imagej = _init_launcher(tmp_path / "Fiji", "ImageJ-win64.exe")
    legacy = _init_launcher(tmp_path / "Legacy", "ImageJ.exe")
    modern = _init_launcher(tmp_path / "Modern", "fiji-windows-x64.exe")

    assert resolve_fiji_installation(imagej).launcher == imagej.resolve()
    assert resolve_fiji_installation(legacy).launcher == legacy.resolve()
    assert resolve_fiji_installation(modern).launcher == modern.resolve()


def test_runtime_accepts_launcher_path_and_caches_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("FIJI_DIR", raising=False)
    monkeypatch.delenv("LEAF_MEASURE_ASSETS_DIR", raising=False)
    monkeypatch.setenv("PATH", "")
    _init_repo(tmp_path)
    assets_root = _init_assets(tmp_path)
    launcher = _init_launcher(tmp_path / "Fiji.app", "ImageJ-win64.exe")

    runtime = resolve_runtime(
        root=tmp_path,
        cli_fiji_dir=launcher,
        cli_assets_dir=assets_root,
    )

    assert runtime.fiji_dir == launcher.parent.resolve()
    assert runtime.fiji_launcher == launcher.resolve()
    assert runtime.source == "cli"

    payload = json.loads(runtime_cache_path(tmp_path).read_text(encoding="utf-8"))
    assert Path(payload["fiji_launcher"]).resolve() == launcher.resolve()


def test_runtime_prefers_path_over_cache(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("FIJI_DIR", raising=False)
    monkeypatch.delenv("LEAF_MEASURE_ASSETS_DIR", raising=False)
    _init_repo(tmp_path)
    assets_root = _init_assets(tmp_path)
    path_launcher = _init_launcher(tmp_path / "on-path", "ImageJ-win64.exe")
    cached_launcher = _init_launcher(tmp_path / "cached", "ImageJ.exe")
    runtime_cache_path(tmp_path).write_text(
        json.dumps({"fiji_launcher": str(cached_launcher)}),
        encoding="utf-8",
    )
    monkeypatch.setenv("PATH", str(path_launcher.parent))

    runtime = resolve_runtime(root=tmp_path, cli_assets_dir=assets_root)

    assert runtime.fiji_launcher == path_launcher.resolve()
    assert runtime.source == "path"


def test_runtime_falls_back_to_cache_when_other_sources_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("FIJI_DIR", raising=False)
    monkeypatch.delenv("LEAF_MEASURE_ASSETS_DIR", raising=False)
    monkeypatch.setenv("PATH", "")
    _init_repo(tmp_path)
    assets_root = _init_assets(tmp_path)
    cached_launcher = _init_launcher(tmp_path / "cached-fiji", "ImageJ-win64.exe")
    runtime_cache_path(tmp_path).write_text(
        json.dumps({"fiji_launcher": str(cached_launcher)}),
        encoding="utf-8",
    )

    runtime = resolve_runtime(root=tmp_path, cli_assets_dir=assets_root)

    assert runtime.fiji_dir == cached_launcher.parent.resolve()
    assert runtime.fiji_launcher == cached_launcher.resolve()
    assert runtime.source == "cache"
