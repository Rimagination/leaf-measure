from __future__ import annotations

import os
import shutil
from pathlib import Path


SKILL_HOSTS = (".agents/skills", ".claude/skills")


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()


def default_skill_install_root() -> Path:
    return (codex_home() / "skills").resolve()


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
    skill_names = {source.name for source in sorted(skills_root.iterdir()) if source.is_dir()}
    for host in SKILL_HOSTS:
        host_root = repo_root / host
        if not host_root.exists():
            continue
        for target in sorted(host_root.iterdir()):
            if target.is_dir() and target.name not in skill_names:
                shutil.rmtree(target)
    for source in sorted(skills_root.iterdir()):
        if not source.is_dir():
            continue
        created.extend(sync_skill(repo_root, source.name))
    return created


def install_skill(repo_root: Path, skill_name: str, destination_root: Path) -> Path:
    repo_root = repo_root.resolve()
    source = canonical_skill_dir(repo_root, skill_name)
    if not source.exists():
        raise FileNotFoundError(f"Canonical skill source not found: {source}")

    destination_root = destination_root.resolve()
    destination_root.mkdir(parents=True, exist_ok=True)
    target = destination_root / skill_name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    return target.resolve()
