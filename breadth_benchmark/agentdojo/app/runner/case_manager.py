from __future__ import annotations

import csv
from pathlib import Path

from app.core.sandbox import OUTPUT_ROOT
from app.attacks.families import display_family_name, display_goal_summary
from app.envs.seeder import prepare_case, load_case
from app.tasks.injection_tasks import INJECTION_TASKS
from app.tasks.registry import SECURITY_CASES, VECTOR_REGISTRY, public_case_id
from app.tasks.user_tasks import USER_TASKS


def list_cases(suite: str | None = None, limit: int | None = None, surface: str | None = None) -> list[dict]:
    """Human-only case catalog.

    This output is for the experimenter, not the AI under test. It includes the
    single injection surface so the experimenter can pick, for example, an email
    case or a calendar case while keeping all other surfaces clean.
    """
    rows = []
    for internal_id, c in sorted(SECURITY_CASES.items()):
        if suite and c.suite != suite:
            continue
        vector = VECTOR_REGISTRY[c.placeholder_id]
        if surface and vector["surface"] != surface:
            continue
        user = USER_TASKS[c.user_task_id]
        injection = INJECTION_TASKS[c.injection_task_id]
        family_display = display_family_name(c.attack_family_id, vector["surface"])
        goal_display = display_goal_summary(c.injection_task_id, injection.goal, vector["surface"])
        rows.append({
            "case_id": public_case_id(internal_id),
            "suite": c.suite,
            "surface": vector["surface"],
            "injection_surface": vector["label"],
            "user_task_id": user.id,
            "user_task": user.prompt,
            "injection_task_id": c.injection_task_id,
            "attack_goal_summary": goal_display,
            "canonical_attack_goal": injection.goal,
            "attack_family_id": c.attack_family_id,
            "attack_family_display": family_display,
            "variant_summary": f"{c.injection_task_id} · {family_display}",
            "single_vector_control": True,
        })
    return rows[:limit] if limit else rows


def export_cases_csv(path: str | Path | None = None) -> Path:
    path = Path(path) if path else OUTPUT_ROOT / "cases.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list_cases(limit=None)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


__all__ = ["prepare_case", "load_case", "list_cases", "export_cases_csv"]
