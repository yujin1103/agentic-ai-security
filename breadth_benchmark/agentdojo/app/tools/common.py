from __future__ import annotations

from typing import Any
import json
from app.core.json_store import get_state, save_state
from app.core.tracing import trace_tool


def _contains(text: str, query: str) -> bool:
    if not query:
        return True
    return query.casefold() in text.casefold()

def _visible_text(output: Any) -> str:
    """Return the exact user/model-visible text for a tool result.

    The GUI and the model should see the same substantive body.  For document-
    like results that already expose a textual field (content/text/data), that
    field is used directly.  For structured results, the visible body is the
    JSON representation of the same structured result, not a separate summary.
    """
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        for key in ("content", "text", "data"):
            value = output.get(key)
            if isinstance(value, str):
                return value
        return json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True)
    if isinstance(output, list):
        return json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True)
    return str(output)


def _make_ui_visible(output: Any) -> Any:
    """Add top-level content/text without changing the underlying API fields.

    Many MCP clients display top-level content/text more reliably than arbitrary
    fields such as data or payload.body.data.  Both fields contain the same
    visible body so there is no mismatch between what the human sees and what
    the model receives.
    """
    if isinstance(output, dict):
        visible = _visible_text(output)
        out = dict(output)
        out["content"] = visible
        out["text"] = visible
        return out
    return output


def _trace(tool: str, args: dict[str, Any], output: Any, blocked: bool = False) -> Any:
    visible_output = _make_ui_visible(output)
    trace_tool(tool, args, visible_output, blocked=blocked, local_only=True)
    return visible_output

def load_state():
    state = get_state()
    if not state:
        # No hidden setup/control tool is exposed to the AI. If the experimenter
        # has not prepared a case yet, fall back to a clean fake environment so
        # the realistic API tools still behave like normal apps.
        from app.envs.seeder import clean_base_state
        state = clean_base_state()
        save_state(state)
    return state

def commit(state):
    save_state(state)
