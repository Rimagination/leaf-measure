from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess


def load_setup_module(repo_root: Path):
    script_path = repo_root / "skills" / "leaf-measure" / "scripts" / "setup_and_analyze.py"
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


def test_refresh_installed_skill_updates_current_skill_directory(repo_root: Path, tmp_path: Path) -> None:
    module = load_setup_module(repo_root)
    repo_cache = tmp_path / "vendor" / "leaf-measure"
    source = repo_cache / "skills" / "leaf-measure"
    (source / "references").mkdir(parents=True)
    (source / "SKILL.md").write_text("---\nname: leaf-measure\ndescription: refreshed\n---\n", encoding="utf-8")
    (source / "references" / "trait-definitions.md").write_text("fresh", encoding="utf-8")

    installed_root = tmp_path / "codex-home" / "skills" / "leaf-measure"
    (installed_root / "references").mkdir(parents=True)
    (installed_root / "SKILL.md").write_text("---\nname: old\n---\n", encoding="utf-8")
    (installed_root / "stale.txt").write_text("remove", encoding="utf-8")

    updated = module.refresh_installed_skill(repo_cache, skill_dir=installed_root)

    assert updated == installed_root.resolve()
    assert (installed_root / "SKILL.md").read_text(encoding="utf-8") == "---\nname: leaf-measure\ndescription: refreshed\n---\n"
    assert (installed_root / "references" / "trait-definitions.md").read_text(encoding="utf-8") == "fresh"
    assert not (installed_root / "stale.txt").exists()


def test_analyze_refreshes_installed_skill_before_running(repo_root: Path, tmp_path: Path, monkeypatch) -> None:
    module = load_setup_module(repo_root)
    installed_root = tmp_path / "codex-home" / "skills" / "leaf-measure"
    installed_root.mkdir(parents=True)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"

    refreshed: list[Path] = []

    def fake_ensure_repo(*, repo_dir: Path | None = None, ref: str = module.DEFAULT_REF, update: bool = True) -> Path:
        target = tmp_path / "vendor" / "leaf-measure"
        target.mkdir(parents=True, exist_ok=True)
        return target

    def fake_refresh(repo_dir: Path, skill_dir: Path | None = None) -> Path:
        refreshed.append(skill_dir or repo_dir)
        return installed_root

    def fake_ensure_runtime(repo_dir: Path) -> dict:
        return {"ok": True}

    def fake_analyze_with_repo(*, repo_dir: Path, input_dir: Path, output_dir: Path, mode: str) -> Path:
        return output_dir / "results.csv"

    monkeypatch.setattr(module, "ensure_repo", fake_ensure_repo)
    monkeypatch.setattr(module, "refresh_installed_skill", fake_refresh)
    monkeypatch.setattr(module, "ensure_runtime", fake_ensure_runtime)
    monkeypatch.setattr(module, "analyze_with_repo", fake_analyze_with_repo)
    monkeypatch.setattr(module, "installed_skill_dir", lambda: installed_root)

    monkeypatch.setattr(
        module,
        "parse_args",
        lambda: module.argparse.Namespace(
            command="analyze",
            input=input_dir,
            output=output_dir,
            mode="full",
            repo_dir=None,
            ref=module.DEFAULT_REF,
            skip_update=False,
        ),
    )

    assert module.main() == 0
    assert refreshed == [installed_root]
