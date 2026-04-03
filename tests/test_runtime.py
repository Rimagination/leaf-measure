from __future__ import annotations

import os
from pathlib import Path

from engine.runtime import resolve_runtime


def test_runtime_config_beats_env_var(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='tmp'\n", encoding="utf-8")
    (tmp_path / "config").mkdir()
    (tmp_path / ".leaf-measure-assets" / "macros" / "original").mkdir(parents=True)
    (tmp_path / ".leaf-measure-assets" / "macros" / "original" / "Fameles_v2_Full_image.ijm").write_text("", encoding="utf-8")
    (tmp_path / ".leaf-measure-assets" / "macros" / "original" / "Fameles_v2_Thumbnails.ijm").write_text("", encoding="utf-8")
    (tmp_path / "config" / "runtime.toml").write_text(
        '[runtime]\nfiji_dir = "D:/from-config/Fiji"\npython_exe = "D:/from-config/python.exe"\nassets_dir = "D:/from-config/assets"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("FIJI_DIR", r"D:\from-env\Fiji")
    monkeypatch.setenv("PYTHON_EXE", r"D:\from-env\python.exe")
    monkeypatch.setenv("LEAF_MEASURE_ASSETS_DIR", r"D:\from-env\assets")

    runtime = resolve_runtime(root=tmp_path)

    assert runtime.fiji_dir == Path(r"D:\from-config\Fiji").resolve()
    assert runtime.python_exe == Path(r"D:\from-config\python.exe").resolve()
    assert runtime.assets_dir == Path(r"D:\from-config\assets").resolve()
    assert runtime.source == "config"
