from __future__ import annotations

"""Human/CLI-only experiment control helpers.

Do not register these helpers on the model-facing MCP server. They exist so the
experimenter can prepare a case and evaluate the resulting fake environment state
without leaking attack metadata to the AI under test.
"""

from app.core.json_store import get_current_case
from app.core.tracing import get_trace
from app.envs.seeder import prepare_case
from app.evaluation.evaluator import evaluate_current_case
from app.runner.case_manager import list_cases


def admin_list_cases(suite: str = "", limit: int = 30, surface: str = "") -> dict:
    return {"cases": list_cases(suite or None, limit, surface or None)}


def admin_prepare_case(case_id: str) -> dict:
    return prepare_case(case_id)


def admin_current_task() -> dict:
    current = get_current_case()
    if not current:
        return {"error": "No prepared case. Run scripts/prepare_case.py first, or use the clean default state."}
    return {
        "case_id": current["public_case_id"],
        "suite": current["suite"],
        "user_task_id": current["user_task_id"],
        "user_prompt": current["user_prompt"],
    }


def admin_evaluate_case() -> dict:
    return evaluate_current_case().to_dict()


def admin_get_trace(limit: int = 100) -> dict:
    return {"trace": get_trace(limit)}
