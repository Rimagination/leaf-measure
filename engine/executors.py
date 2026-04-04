from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class BatchExecutionResult:
    executor: str
    launcher: Path
    macro_path: Path
    stdout_log: Path
    stderr_log: Path
    exit_code: int


def find_fiji_launcher(fiji_dir: Path) -> Path:
    candidates = [
        fiji_dir / "fiji-windows-x64.exe",
        fiji_dir / "fiji-windows-arm64.exe",
        fiji_dir / "fiji.bat",
        fiji_dir / "fiji",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Could not find a Fiji launcher under {fiji_dir}")


def run_batch_macro(*, fiji_dir: Path, macro_text: str, work_dir: Path) -> BatchExecutionResult:
    fiji_dir = fiji_dir.resolve()
    work_dir = work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    macro_path = (work_dir / "run.ijm").resolve()
    stdout_log = (work_dir / "fiji-stdout.log").resolve()
    stderr_log = (work_dir / "fiji-stderr.log").resolve()
    launcher = find_fiji_launcher(fiji_dir).resolve()

    macro_path.write_text(macro_text, encoding="utf-8")
    result = subprocess.run(
        [str(launcher), "-batch", str(macro_path)],
        cwd=str(fiji_dir),
        capture_output=True,
        text=True,
    )
    stdout_log.write_text(result.stdout, encoding="utf-8", errors="ignore")
    stderr_log.write_text(result.stderr, encoding="utf-8", errors="ignore")

    return BatchExecutionResult(
        executor="direct-fiji-batch",
        launcher=launcher,
        macro_path=macro_path,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        exit_code=result.returncode,
    )
