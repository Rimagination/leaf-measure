from __future__ import annotations

from dataclasses import dataclass
import ctypes
import json
import os
from pathlib import Path
import shutil


FIJI_LAUNCHER_NAMES = (
    "ImageJ-win64.exe",
    "ImageJ.exe",
    "fiji-windows-x64.exe",
    "fiji-windows-arm64.exe",
    "fiji.bat",
    "fiji",
)


@dataclass(frozen=True)
class ResolvedFijiInstallation:
    root_dir: Path
    launcher: Path


def runtime_cache_path(root: Path) -> Path:
    return root / "config" / "runtime-cache.json"


def resolve_fiji_installation(path: Path | None) -> ResolvedFijiInstallation | None:
    if path is None:
        return None

    candidate = path.expanduser().resolve()
    launcher_names = {name.lower() for name in FIJI_LAUNCHER_NAMES}
    if candidate.is_file():
        if candidate.name.lower() not in launcher_names:
            return None
        return ResolvedFijiInstallation(root_dir=candidate.parent.resolve(), launcher=candidate.resolve())

    if not candidate.is_dir():
        return None

    for directory in (candidate, candidate / "Fiji"):
        if not directory.is_dir():
            continue
        for launcher_name in FIJI_LAUNCHER_NAMES:
            launcher = directory / launcher_name
            if launcher.is_file():
                return ResolvedFijiInstallation(
                    root_dir=directory.resolve(),
                    launcher=launcher.resolve(),
                )
    return None


def discover_fiji_from_path() -> tuple[ResolvedFijiInstallation | None, list[Path]]:
    candidates: list[Path] = []
    seen: set[Path] = set()
    for launcher_name in FIJI_LAUNCHER_NAMES:
        located = shutil.which(launcher_name)
        if not located:
            continue
        candidate = Path(located).resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        candidates.append(candidate)

    for candidate in candidates:
        resolved = resolve_fiji_installation(candidate)
        if resolved is not None:
            return resolved, candidates
    return None, candidates


def discover_local_and_common_fiji_candidates(root: Path) -> list[Path]:
    candidates = [
        root / "fiji-latest-win64-jdk" / "Fiji",
        root / "Fiji",
        root / "ImageJ",
        root.parent / "fiji-latest-win64-jdk" / "Fiji",
        root.parent / "leaf" / "fiji-latest-win64-jdk" / "Fiji",
    ]

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        local_root = Path(local_app_data)
        candidates.extend(
            [
                local_root / "Programs" / "Fiji.app",
                local_root / "Programs" / "Fiji",
                local_root / "Fiji.app",
                local_root / "Fiji",
            ]
        )

    drive_roots: list[Path] = []
    seen_drives: set[str] = set()
    if os.name == "nt":
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for index, drive_letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
            if not (bitmask & (1 << index)):
                continue
            drive = Path(f"{drive_letter}:/")
            seen_drives.add(drive.drive.upper())
            drive_roots.append(drive)
    else:
        for drive_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = Path(f"{drive_letter}:/")
            if drive.exists() and drive.drive.upper() not in seen_drives:
                seen_drives.add(drive.drive.upper())
                drive_roots.append(drive)

    for drive in drive_roots:
        for base_name in ("Program Files", "Program Files (x86)"):
            program_files = drive / base_name
            if not program_files.exists():
                continue
            candidates.extend(
                [
                    program_files / "Fiji.app",
                    program_files / "Fiji",
                    program_files / "ImageJ",
                    program_files / "ImageJ2",
                ]
            )

    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped


def load_cached_fiji(root: Path) -> ResolvedFijiInstallation | None:
    cache_path = runtime_cache_path(root)
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    cached = payload.get("fiji_launcher") or payload.get("fiji_path")
    if not cached:
        return None
    return resolve_fiji_installation(Path(cached))


def remember_fiji_installation(root: Path, resolved: ResolvedFijiInstallation) -> Path:
    cache_path = runtime_cache_path(root)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fiji_dir": str(resolved.root_dir),
        "fiji_launcher": str(resolved.launcher),
    }
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return cache_path
