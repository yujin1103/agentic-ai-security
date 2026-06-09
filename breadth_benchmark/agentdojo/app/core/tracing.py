from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.json_store import append_jsonl, read_jsonl

TRACE_PATH = "traces/tool_calls.jsonl"
EVAL_PATH = "traces/evaluations.jsonl"


def _collect_output_strings(value: Any) -> list[str]:
    """Collect raw strings from tool output without Python repr escaping.

    Prompt-injection text can be multiline. If we store str(dict), newlines are
    turned into literal \n sequences and contamination_seen misses the output.
    """
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for v in value.values():
            out.extend(_collect_output_strings(v))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for v in value:
            out.extend(_collect_output_strings(v))
        return out
    if value is None:
        return []
    return [str(value)]


def trace_tool(tool_name: str, args: dict[str, Any], output: Any, *, blocked: bool = False, local_only: bool = True) -> None:
    output_text = "\n".join(_collect_output_strings(output))
    output_preview = output if isinstance(output, (str, int, float, bool, type(None))) else output_text[:800]
    append_jsonl(TRACE_PATH, {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "args": args,
        "blocked": blocked,
        "local_only": local_only,
        "output_preview": output_preview,
        "output_text": output_text[:20000],
    })

def trace_evaluation(row: dict[str, Any]) -> None:
    append_jsonl(EVAL_PATH, {"ts": datetime.now(timezone.utc).isoformat(), **row})

def get_trace(limit: int = 100) -> list[dict[str, Any]]:
    rows = read_jsonl(TRACE_PATH)
    return rows[-max(1, limit):]
