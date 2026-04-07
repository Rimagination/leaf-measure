from __future__ import annotations

import os
from pathlib import Path

from engine.runtime import resolve_runtime


def test_runtime_env_var_beats_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("FIJI_DIR", raising=False)
    monkeypatch.delenv("PYTHON_EXE", raising=False)
    monkeypatch.delenv("LEAF_MEASURE_ASSETS_DIR", raising=False)
    monkeypatch.setenv("PATH", "")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='tmp'\n", encoding="utf-8")
    (tmp_path / "config").mkdir()
    config_fiji = tmp_path / "from-config" / "Fiji"
    config_assets = tmp_path / "from-config" / "assets"
    config_python = tmp_path / "from-config" / "python.exe"
    env_fiji = tmp_path / "from-env" / "Fiji"
    config_fiji.mkdir(parents=True)
    env_fiji.mkdir(parents=True)
    (config_fiji / "ImageJ-win64.exe").write_text("", encoding="utf-8")
    (env_fiji / "ImageJ-win64.exe").write_text("", encoding="utf-8")
    (config_assets / "macros" / "original").mkdir(parents=True)
    (config_assets / "macros" / "original" / "Fameles_v2_Full_image.ijm").write_text("", encoding="utf-8")
    (config_assets / "macros" / "original" / "Fameles_v2_Thumbnails.ijm").write_text("", encoding="utf-8")
    config_python.write_text("", encoding="utf-8")
    (tmp_path / "config" / "runtime.toml").write_text(
        f'[runtime]\nfiji_dir = "{config_fiji.as_posix()}"\npython_exe = "{config_python.as_posix()}"\nassets_dir = "{config_assets.as_posix()}"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("FIJI_DIR", env_fiji.as_posix())
    monkeypatch.setenv("PYTHON_EXE", r"D:\from-env\python.exe")
    monkeypatch.setenv("LEAF_MEASURE_ASSETS_DIR", r"D:\from-env\assets")

    runtime = resolve_runtime(root=tmp_path)

    assert runtime.fiji_dir == env_fiji.resolve()
    assert runtime.fiji_launcher is not None
    assert runtime.python_exe == config_python.resolve()
    assert runtime.assets_dir == config_assets.resolve()
    assert runtime.source == "env"


def test_runtime_ignores_placeholder_config_and_falls_back_to_discovery(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("FIJI_DIR", raising=False)
    monkeypatch.delenv("PYTHON_EXE", raising=False)
    monkeypatch.delenv("LEAF_MEASURE_ASSETS_DIR", raising=False)
    monkeypatch.setenv("PATH", "")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='tmp'\n", encoding="utf-8")
    (tmp_path / "config").mkdir()
    discovered_fiji = tmp_path / "fiji-latest-win64-jdk" / "Fiji"
    discovered_assets = tmp_path / ".leaf-measure-assets" / "macros" / "original"
    discovered_fiji.mkdir(parents=True)
    (discovered_fiji / "ImageJ-win64.exe").write_text("", encoding="utf-8")
    discovered_assets.mkdir(parents=True)
    (discovered_assets / "Fameles_v2_Full_image.ijm").write_text("", encoding="utf-8")
    (discovered_assets / "Fameles_v2_Thumbnails.ijm").write_text("", encoding="utf-8")
    (tmp_path / "config" / "runtime.toml").write_text(
        '[runtime]\nfiji_dir = "D:/path/to/Fiji"\npython_exe = "D:/path/to/python.exe"\nassets_dir = "D:/path/to/leaf-measure-assets"\n',
        encoding="utf-8",
    )

    runtime = resolve_runtime(root=tmp_path)

    assert runtime.fiji_dir == discovered_fiji.resolve()
    assert runtime.fiji_launcher is not None
    assert runtime.fiji_launcher.parent == discovered_fiji.resolve()
    assert runtime.assets_dir == (tmp_path / ".leaf-measure-assets").resolve()
    assert runtime.source == "local-discovery"
