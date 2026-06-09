from __future__ import annotations

from typing import Any

from app.attacks.families import render_attack
from app.core.json_store import save_current_case, save_state
from app.core.sandbox import reset_lab_root
from app.envs.base_state import PLACEHOLDERS, base_state
from app.tasks.injection_tasks import INJECTION_TASKS
from app.tasks.registry import SECURITY_CASES, public_case_id, resolve_case_id, VECTOR_REGISTRY
from app.tasks.user_tasks import USER_TASKS


def _replace_placeholder(obj: Any, placeholder: str, injection_text: str) -> Any:
    if isinstance(obj, str):
        return obj.replace(placeholder, injection_text)
    if isinstance(obj, list):
        return [_replace_placeholder(x, placeholder, injection_text) for x in obj]
    if isinstance(obj, dict):
        return {k: _replace_placeholder(v, placeholder, injection_text) for k, v in obj.items()}
    return obj


def _remove_all_placeholders(obj: Any) -> Any:
    """Remove every unused attack placeholder so clean surfaces stay clean.

    This is the important single-vector control: if a case is a calendar-injection
    case, the mail/drive/web/slack/banking/travel/memory surfaces must not still
    contain any injection markers or template residue.
    """
    if isinstance(obj, str):
        for token in PLACEHOLDERS.values():
            obj = obj.replace(token, "")
        return " ".join(obj.split()) if "{{INJECTION_PLACEHOLDER:" in obj else obj
    if isinstance(obj, list):
        return [_remove_all_placeholders(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _remove_all_placeholders(v) for k, v in obj.items()}
    return obj


def clean_base_state() -> dict[str, Any]:
    """Return the fake environment with no prompt-injection text anywhere."""
    return _remove_all_placeholders(base_state())


def build_case_state(case_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    internal_case_id = resolve_case_id(case_id)
    if internal_case_id not in SECURITY_CASES:
        raise KeyError(f"Unknown case_id: {case_id}")

    case = SECURITY_CASES[internal_case_id]
    user_task = USER_TASKS[case.user_task_id]
    injection_task = INJECTION_TASKS[case.injection_task_id]
    vector = VECTOR_REGISTRY[case.placeholder_id]
    attack_text = render_attack(
        case.attack_family_id,
        injection_task.goal,
        goal_id=injection_task.id,
        surface=vector["surface"],
        placeholder_id=case.placeholder_id,
    )

    state = base_state()
    placeholder_token = PLACEHOLDERS[case.placeholder_id]
    state = _replace_placeholder(state, placeholder_token, attack_text)
    state = _remove_all_placeholders(state)

    current = {
        # Public fields are safe to show to the model.
        "public_case_id": public_case_id(case.case_id),
        "suite": case.suite,
        "user_task_id": user_task.id,
        "user_prompt": user_task.prompt,
        # Private evaluator-only fields. Never expose through model-facing MCP.
        "internal_case_id": case.case_id,
        "injection_task_id": injection_task.id,
        "injection_goal": injection_task.goal,
        "attack_family_id": case.attack_family_id,
        "placeholder_id": case.placeholder_id,
        "injection_surface": vector["label"],
        "attack_text_preview": attack_text[:500],
        "single_vector_control": True,
        "clean_surfaces": [k for k in PLACEHOLDERS if k != case.placeholder_id],
    }
    return state, current


def prepare_case(case_id: str) -> dict[str, Any]:
    """Human-only setup: write a single-vector case into lab_env state."""
    state, current = build_case_state(case_id)
    vector = VECTOR_REGISTRY[current["placeholder_id"]]
    reset_lab_root()
    save_state(state)
    save_current_case(current)
    return {
        "case_id": current["public_case_id"],
        "suite": current["suite"],
        "user_task_id": current["user_task_id"],
        "surface": vector["surface"],
        "injection_surface": current["injection_surface"],
        "user_prompt": current["user_prompt"],
        "single_vector_control": True,
        "clean_surfaces_count": len(current["clean_surfaces"]),
    }


# Backward-compatible human-only alias used by older scripts.
load_case = prepare_case
