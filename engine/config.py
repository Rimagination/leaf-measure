from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib


@dataclass(frozen=True)
class RuntimeConfig:
    fiji_dir: Path | None = None
    python_exe: Path | None = None
    assets_dir: Path | None = None


def read_runtime_config(path: Path) -> RuntimeConfig:
    if not path.exists():
        return RuntimeConfig()

    data: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    runtime = data.get("runtime", {})
    fiji_dir = runtime.get("fiji_dir")
    python_exe = runtime.get("python_exe")
    assets_dir = runtime.get("assets_dir")
    return RuntimeConfig(
        fiji_dir=Path(fiji_dir) if fiji_dir else None,
        python_exe=Path(python_exe) if python_exe else None,
        assets_dir=Path(assets_dir) if assets_dir else None,
    )
