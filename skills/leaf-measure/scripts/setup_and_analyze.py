from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


REPO_URL = "https://github.com/Rimagination/leaf-measure.git"
DEFAULT_REF = "main"


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()


def default_repo_dir() -> Path:
    return (codex_home() / "vendor" / "leaf-measure").resolve()


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=str(cwd) if cwd else None, capture_output=True, text=True)


def ensure_repo(*, repo_dir: Path | None = None, ref: str = DEFAULT_REF, update: bool = True) -> Path:
    repo_dir = (repo_dir or default_repo_dir()).resolve()
    repo_dir.parent.mkdir(parents=True, exist_ok=True)

    if (repo_dir / ".git").exists():
        if update:
            result = run(["git", "-C", str(repo_dir), "pull", "--ff-only", "origin", ref])
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git pull failed")
        return repo_dir

    result = run(
        ["git", "clone", "--depth", "1", "--branch", ref, REPO_URL, str(repo_dir)],
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git clone failed")
    return repo_dir


def doctor_payload(repo_dir: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="leaf-measure-doctor-") as temp_dir_name:
        report_path = Path(temp_dir_name) / "doctor.json"
        result = run(
            [
                sys.executable,
                "-m",
                "engine.cli",
                "doctor",
                "--output",
                str(report_path),
            ],
            cwd=repo_dir,
        )
        if result.returncode not in (0, 2):
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "doctor failed")
        return json.loads(report_path.read_text(encoding="utf-8"))


def ensure_runtime(repo_dir: Path) -> dict:
    payload: dict | None = None
    first_doctor_error: RuntimeError | None = None
    try:
        payload = doctor_payload(repo_dir)
        if payload.get("ok"):
            return payload
    except RuntimeError as error:
        first_doctor_error = error

    if os.name != "nt":
        raise RuntimeError(
            "Automatic bootstrap is currently validated on Windows only. Open the leaf-measure repo and run the platform-specific setup steps."
        ) from first_doctor_error

    result = run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(repo_dir / "scripts" / "bootstrap.ps1"),
            "-RepoRoot",
            str(repo_dir),
        ],
        cwd=repo_dir,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "bootstrap failed")
    try:
        payload = doctor_payload(repo_dir)
    except RuntimeError as error:
        if first_doctor_error is not None:
            raise RuntimeError(
                f"bootstrap finished, but doctor still failed: {error}"
            ) from error
        raise
    return payload


def analyze_with_repo(
    *,
    repo_dir: Path,
    input_dir: Path,
    output_dir: Path,
    mode: str,
) -> Path:
    result = run(
        [
            sys.executable,
            "-m",
            "engine.cli",
            "analyze",
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
            "--mode",
            mode,
        ],
        cwd=repo_dir,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "analysis failed")
    return output_dir / "results.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set up and run leaf-measure from a globally installed skill.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ensure = subparsers.add_parser("ensure-repo", help="Clone or update the shared leaf-measure repo cache.")
    ensure.add_argument("--repo-dir", type=Path)
    ensure.add_argument("--ref", default=DEFAULT_REF)
    ensure.add_argument("--skip-update", action="store_true")

    analyze = subparsers.add_parser("analyze", help="Ensure the repo/runtime exists, then run analysis.")
    analyze.add_argument("--input", type=Path, required=True)
    analyze.add_argument("--output", type=Path, required=True)
    analyze.add_argument("--mode", choices=["full", "thumbnails"], required=True)
    analyze.add_argument("--repo-dir", type=Path)
    analyze.add_argument("--ref", default=DEFAULT_REF)
    analyze.add_argument("--skip-update", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "ensure-repo":
        repo_dir = ensure_repo(repo_dir=args.repo_dir, ref=args.ref, update=not args.skip_update)
        print(repo_dir)
        return 0
    if args.command == "analyze":
        repo_dir = ensure_repo(repo_dir=args.repo_dir, ref=args.ref, update=not args.skip_update)
        payload = ensure_runtime(repo_dir)
        if not payload.get("ok"):
            raise RuntimeError("Runtime is still not ready after bootstrap.")
        results_csv = analyze_with_repo(
            repo_dir=repo_dir,
            input_dir=args.input,
            output_dir=args.output,
            mode=args.mode,
        )
        print(results_csv)
        return 0
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
