from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.sandbox import ensure_lab_dirs, resolve_lab_path

STATE_FILE = "state.json"
CURRENT_CASE_FILE = "current_case.json"

def read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def write_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_state() -> dict[str, Any]:
    ensure_lab_dirs()
    return read_json_file(resolve_lab_path(STATE_FILE), {})

def save_state(state: dict[str, Any]) -> None:
    write_json_file(resolve_lab_path(STATE_FILE), state)

def get_current_case() -> dict[str, Any]:
    return read_json_file(resolve_lab_path(CURRENT_CASE_FILE), {})

def save_current_case(data: dict[str, Any]) -> None:
    write_json_file(resolve_lab_path(CURRENT_CASE_FILE), data)

def append_jsonl(relative_path: str, row: dict[str, Any]) -> None:
    path = resolve_lab_path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

def read_jsonl(relative_path: str) -> list[dict[str, Any]]:
    path = resolve_lab_path(relative_path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out
