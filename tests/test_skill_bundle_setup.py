from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess


def load_setup_module(repo_root: Path):
    script_path = repo_root / "skills" / "leaf-fameles" / "scripts" / "setup_and_analyze.py"
    spec = importlib.util.spec_from_file_location("leaf_fameles_setup", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ensure_runtime_bootstraps_after_initial_doctor_failure(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = load_setup_module(repo_root)
    repo_dir = tmp_path / "leaf-measure"
    (repo_dir / "scripts").mkdir(parents=True)
    (repo_dir / "scripts" / "bootstrap.ps1").write_text("# bootstrap", encoding="utf-8")

    doctor_calls = {"count": 0}

    def fake_doctor(_repo_dir: Path) -> dict:
        doctor_calls["count"] += 1
        if doctor_calls["count"] == 1:
            raise RuntimeError("doctor failed before dependencies were installed")
        return {"ok": True, "issues": []}

    bootstrap_calls: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        bootstrap_calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(module, "doctor_payload", fake_doctor)
    monkeypatch.setattr(module, "run", fake_run)
    monkeypatch.setattr(module.os, "name", "nt")

    payload = module.ensure_runtime(repo_dir)

    assert payload["ok"] is True
    assert doctor_calls["count"] == 2
    assert any("bootstrap.ps1" in " ".join(command) for command in bootstrap_calls)
