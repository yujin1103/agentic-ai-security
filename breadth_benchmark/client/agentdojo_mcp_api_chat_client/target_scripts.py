from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_target_script(project_root: Path, script_name: str, *args: str) -> tuple[int, str]:
    script = project_root / "scripts" / script_name
    if not script.exists():
        return 2, f"Missing target script: {script}"
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(project_root),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc.returncode, proc.stdout
