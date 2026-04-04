from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from engine.skill_sync import install_skill


def test_install_skill_copies_canonical_skill_into_target_directory(tmp_path: Path) -> None:
    source = tmp_path / "skills" / "leaf-measure"
    (source / "references").mkdir(parents=True)
    (source / "SKILL.md").write_text("---\nname: leaf-measure\ndescription: test\n---\n", encoding="utf-8")
    (source / "references" / "trait-definitions.md").write_text("traits", encoding="utf-8")

    install_root = tmp_path / "installed-skills"
    target = install_skill(tmp_path, "leaf-measure", install_root)

    assert target == (install_root / "leaf-measure").resolve()
    assert (target / "SKILL.md").exists()
    assert (target / "references" / "trait-definitions.md").read_text(encoding="utf-8") == "traits"


def test_install_skill_cli_defaults_to_codex_home_skills(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "skills" / "leaf-measure"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text("---\nname: leaf-measure\ndescription: test\n---\n", encoding="utf-8")

    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "engine.cli",
            "install-skill",
            "--repo-root",
            str(tmp_path),
            "--skill-name",
            "leaf-measure",
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    target = codex_home / "skills" / "leaf-measure"
    assert target.exists()
    assert result.stdout.strip() == str(target.resolve())
