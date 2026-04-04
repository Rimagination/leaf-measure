from __future__ import annotations

from pathlib import Path


def test_bootstrap_script_syncs_repo_local_skills(repo_root: Path) -> None:
    script = (repo_root / "scripts" / "bootstrap.ps1").read_text(encoding="utf-8")

    assert "sync-skills" in script
