from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def new_run_dir(base: str | Path = "runs") -> Path:
    root = Path(base)
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = root / f"run_{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


class RunLogger:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.events_path = run_dir / "events.jsonl"
        self.transcript_path = run_dir / "transcript.md"

    def event(self, kind: str, data: dict[str, Any]) -> None:
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            **data,
        }
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def transcript(self, speaker: str, text: str) -> None:
        with self.transcript_path.open("a", encoding="utf-8") as f:
            f.write(f"\n## {speaker}\n\n{text}\n")


def mirror_tool_trace(project_root: Path, tool: str, args: dict[str, Any], output_text: str, *, blocked: bool = False) -> Path:
    """Mirror API-client MCP calls into the target MCP project's trace file.

    This keeps evaluate_case.py/show_trace.py useful even when the external MCP
    transport or project-root mismatch prevents the server-side trace from being
    visible from the selected lab project folder.
    """
    trace_dir = project_root / "lab_env" / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / "tool_calls.jsonl"
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "args": args,
        "blocked": blocked,
        "local_only": True,
        "source": "api_chat_client_mirror",
        "output_preview": output_text[:800],
        "output_text": output_text[:20000],
    }
    with trace_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return trace_path
