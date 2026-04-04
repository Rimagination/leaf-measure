from __future__ import annotations

from pathlib import Path

from engine.skill_sync import sync_all_skills


def test_sync_all_skills_copies_canonical_skill_to_hosts(tmp_path: Path) -> None:
    source = tmp_path / "skills" / "leaf-fameles"
    (source / "references").mkdir(parents=True)
    (source / "agents").mkdir(parents=True)
    (source / "SKILL.md").write_text("---\nname: leaf-fameles\ndescription: test\n---\n", encoding="utf-8")
    (source / "references" / "mode-selection.md").write_text("modes", encoding="utf-8")
    (source / "agents" / "openai.yaml").write_text("display_name: Leaf Measure\n", encoding="utf-8")

    created = sync_all_skills(tmp_path)

    expected = {
        (tmp_path / ".agents" / "skills" / "leaf-fameles").resolve(),
        (tmp_path / ".claude" / "skills" / "leaf-fameles").resolve(),
    }
    assert {path.resolve() for path in created} == expected
    for target in expected:
        assert (target / "SKILL.md").exists()
        assert (target / "references" / "mode-selection.md").read_text(encoding="utf-8") == "modes"
        assert (target / "agents" / "openai.yaml").exists()
