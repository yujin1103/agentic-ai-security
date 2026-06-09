from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CurrentCase:
    project_root: Path
    lab_env: Path
    case_id: str
    suite: str
    user_task_id: str
    user_prompt: str
    raw: dict


def normalize_project_root(path_text: str | Path) -> Path:
    path = Path(path_text).expanduser().resolve()
    if path.name == "lab_env":
        return path.parent
    return path


def load_current_case(project_root: str | Path) -> CurrentCase:
    root = normalize_project_root(project_root)
    current_path = root / "lab_env" / "current_case.json"
    if not current_path.exists():
        raise FileNotFoundError(
            f"No prepared case found at {current_path}. Run prepare_case.py in the MCP project first."
        )
    data = json.loads(current_path.read_text(encoding="utf-8"))
    return CurrentCase(
        project_root=root,
        lab_env=root / "lab_env",
        case_id=data.get("public_case_id", ""),
        suite=data.get("suite", ""),
        user_task_id=data.get("user_task_id", ""),
        user_prompt=data.get("user_prompt", ""),
        raw=data,
    )
