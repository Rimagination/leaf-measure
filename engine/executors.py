from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from engine.errors import LeafMeasureError
from engine.fiji import resolve_fiji_installation


@dataclass(frozen=True)
class BatchExecutionResult:
    executor: str
    launcher: Path
    macro_path: Path
    stdout_log: Path
    stderr_log: Path
    exit_code: int


def run_batch_macro(*, fiji_path: Path, macro_text: str, work_dir: Path) -> BatchExecutionResult:
    resolved = resolve_fiji_installation(fiji_path)
    if resolved is None:
        raise LeafMeasureError(
            stage="runtime_discovery",
            code="missing_fiji",
            message=f"Could not resolve a runnable Fiji launcher from {fiji_path}.",
            hints=[
                "Pass `--fiji` either a Fiji directory or a launcher such as `ImageJ-win64.exe`.",
                "Run `python -m engine.cli doctor` to inspect runtime discovery.",
            ],
            details={"requested_fiji_path": fiji_path},
        )

    fiji_dir = resolved.root_dir
    work_dir = work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    macro_path = (work_dir / "run.ijm").resolve()
    stdout_log = (work_dir / "fiji-stdout.log").resolve()
    stderr_log = (work_dir / "fiji-stderr.log").resolve()
    launcher = resolved.launcher.resolve()

    macro_path.write_text(macro_text, encoding="utf-8")
    try:
        result = subprocess.run(
            [str(launcher), "-batch", str(macro_path)],
            cwd=str(fiji_dir),
            capture_output=True,
            text=True,
        )
    except OSError as error:
        hints = [
            "Verify the Fiji launcher can be started manually from the same account.",
            "Run `python -m engine.cli doctor` to confirm the resolved launcher path.",
        ]
        if getattr(error, "winerror", None) == 740:
            hints.append(
                "Windows reported that this launcher requires elevation. Move Fiji to a user-writable location or rerun from a launcher that does not require administrator rights."
            )
        raise LeafMeasureError(
            stage="fiji_launch",
            code="fiji_launch_failed",
            message=f"Failed to launch Fiji via {launcher}.",
            hints=hints,
            details={
                "launcher": launcher,
                "fiji_dir": fiji_dir,
                "os_error": str(error),
                "winerror": getattr(error, "winerror", None),
            },
        ) from error
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
