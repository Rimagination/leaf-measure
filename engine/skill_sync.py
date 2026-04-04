from __future__ import annotations

import shutil
from pathlib import Path


SKILL_HOSTS = (".agents/skills", ".claude/skills")


def canonical_skill_dir(repo_root: Path, skill_name: str) -> Path:
    return repo_root / "skills" / skill_name


def sync_skill(repo_root: Path, skill_name: str) -> list[Path]:
    repo_root = repo_root.resolve()
    source = canonical_skill_dir(repo_root, skill_name)
    if not source.exists():
        raise FileNotFoundError(f"Canonical skill source not found: {source}")

    targets: list[Path] = []
    for host in SKILL_HOSTS:
        target = repo_root / host / skill_name
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
        targets.append(target)
    return targets


def sync_all_skills(repo_root: Path) -> list[Path]:
    repo_root = repo_root.resolve()
    created: list[Path] = []
    skills_root = repo_root / "skills"
    if not skills_root.exists():
        return created
    for source in sorted(skills_root.iterdir()):
        if not source.is_dir():
            continue
        created.extend(sync_skill(repo_root, source.name))
    return created
