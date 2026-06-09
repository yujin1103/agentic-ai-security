from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.runner.case_manager import list_cases
from app.core.terminal_ui import ko_surface, ko_suite, ko_task, bullet, numbered, title, wrapped_value


def _readable_sort_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        ko_surface(str(row.get("surface", ""))),
        ko_suite(str(row.get("suite", ""))),
        str(row.get("user_task_id", "")),
        str(row.get("case_id", "")),
    )


def _collapse_variants(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            str(row.get("surface", "unknown")),
            str(row.get("user_task_id", "unknown")),
            str(row.get("injection_surface", "unknown")),
        )
        grouped[key].append(row)

    collapsed: list[dict[str, Any]] = []
    for variants in grouped.values():
        variants = sorted(variants, key=lambda r: str(r.get("case_id", "")))
        representative = dict(variants[0])
        representative["variant_count"] = len(variants)
        representative["variant_case_ids_preview"] = [str(v.get("case_id")) for v in variants[:5]]
        representative["variant_summaries_preview"] = [str(v.get("variant_summary", "")) for v in variants[:5]]
        collapsed.append(representative)
    return sorted(collapsed, key=_readable_sort_key)


def _surface_balanced(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(rows, key=_readable_sort_key):
        buckets[str(row.get("surface", "unknown"))].append(row)
    surface_order = sorted(buckets, key=lambda s: ko_surface(s))
    balanced: list[dict[str, Any]] = []
    while any(buckets.values()):
        for surface in surface_order:
            if buckets[surface]:
                balanced.append(buckets[surface].pop(0))
    return balanced


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _numeric_case_candidates(q: str) -> set[str]:
    q = q.strip().lower()
    out: set[str] = set()
    m = re.fullmatch(r"case[_\-\s]*(\d{1,4})", q)
    if m:
        out.add(f"case_{int(m.group(1)):04d}")
        out.add(f"case_{m.group(1).zfill(4)}")
    if re.fullmatch(r"\d{1,4}", q):
        out.add(f"case_{int(q):04d}")
        out.add(f"case_{q.zfill(4)}")
    return out


SEARCH_FIELDS = (
    "case_id",
    "suite",
    "surface",
    "injection_surface",
    "user_task_id",
    "user_task",
    "injection_task_id",
    "attack_goal_summary",
    "canonical_attack_goal",
    "attack_family_id",
    "attack_family_display",
    "variant_summary",
)


def _blob(row: dict[str, Any]) -> str:
    return _norm(" ".join(str(row.get(k, "")) for k in SEARCH_FIELDS))


def _score(row: dict[str, Any], query: str) -> int:
    q = _norm(query)
    if not q:
        return 1

    case_id = _norm(row.get("case_id"))
    surface = _norm(row.get("surface"))
    suite = _norm(row.get("suite"))
    task_id = _norm(row.get("user_task_id"))
    inj_id = _norm(row.get("injection_task_id"))
    family = _norm(row.get("attack_family_id"))
    row_blob = _blob(row)

    candidates = _numeric_case_candidates(q)
    if case_id in candidates:
        return 100000

    score = 0
    if q == case_id:
        score += 90000
    elif q and q in case_id:
        score += 50000

    # Direct structured-field matches are more useful than full-text matches.
    if q in {surface, suite, task_id, inj_id, family}:
        score += 20000
    for field in ("surface", "suite", "user_task_id", "injection_task_id", "attack_family_id"):
        if q and q in _norm(row.get(field)):
            score += 8000

    if q and q in _norm(row.get("user_task")):
        score += 3000
    if q and q in _norm(row.get("injection_surface")):
        score += 2500
    if q and q in _norm(row.get("attack_goal_summary")):
        score += 2000
    if q and q in _norm(row.get("attack_family_display")):
        score += 1500
    if q and q in row_blob:
        score += 500

    # Token fallback: all tokens must be somewhere, with useful partial ordering.
    tokens = [t for t in re.split(r"[^a-z0-9_.@:-]+", q) if t]
    if tokens:
        hits = sum(1 for t in tokens if t in row_blob)
        if hits == len(tokens):
            score += 1000 + hits * 100
        elif hits:
            score += hits * 10

    return score


def search_cases(
    query: str,
    *,
    limit: int = 20,
    surface: str = "",
    suite: str = "",
    include_variants: bool = True,
) -> dict[str, Any]:
    raw_rows = list_cases(suite or None, None, surface or None)
    if not query.strip() and not include_variants:
        rows = _surface_balanced(_collapse_variants(raw_rows))
        total = len(rows)
        return {
            "query": query,
            "mode": "representatives",
            "total_matches": total,
            "returned": min(limit, total),
            "cases": rows[:limit],
        }

    rows = raw_rows if include_variants else _collapse_variants(raw_rows)
    if query.strip():
        scored = [(row, _score(row, query)) for row in rows]
        matched = [item for item in scored if item[1] > 0]
        matched.sort(key=lambda item: (-item[1], str(item[0].get("case_id", ""))))
        rows = [row for row, _score_value in matched]
    else:
        # Full variant view with no query: keep representative-like surface balance first.
        rows = _surface_balanced(_collapse_variants(raw_rows)) if not include_variants else sorted(rows, key=lambda r: str(r.get("case_id", "")))

    total = len(rows)
    return {
        "query": query,
        "mode": "variants" if include_variants else "representatives",
        "total_matches": total,
        "returned": min(limit, total),
        "limit": limit,
        "cases": rows[:limit],
    }


def print_results(payload: dict[str, Any]) -> None:
    print(title("케이스 검색"))
    print(bullet("검색어", payload.get("query") or "없음"))
    print(bullet("표시", f"총 {payload.get('total_matches', 0)}개 중 {payload.get('returned', 0)}개"))
    rows = payload.get("cases", [])
    if not rows:
        print(bullet("결과", "조건에 맞는 케이스가 없습니다."))
        return
    for idx, row in enumerate(rows, start=1):
        print("\n" + numbered(idx, f"{ko_surface(row.get('surface'))} 인젝션 | {row.get('case_id')} | {ko_suite(row.get('suite'))} | {row.get('user_task_id')}"))
        print(bullet("작업 요약", ko_task(row.get("user_task_id"), wrapped_value(row.get("user_task", ""), 120)), indent=2))
        print(bullet("목표", wrapped_value(row.get("attack_goal_summary", ""), 140), indent=2))
        print(bullet("표현 방식", wrapped_value(row.get("attack_family_display", ""), 120), indent=2))
        print(bullet("세부 위치", wrapped_value(row.get("injection_surface", ""), 160), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="사람용 case 검색입니다. MCP model-facing tool이 아닙니다.")
    parser.add_argument("--q", default="", help="검색어. 예: 0265, case_0265, memory, I06, Eve, q2_budget")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--surface", default="", help="mail, calendar, drive, web, slack, banking, travel, memory")
    parser.add_argument("--suite", default="")
    parser.add_argument("--representatives", action="store_true", help="대표 task-surface 조합만 검색")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = search_cases(
        args.q,
        limit=args.limit,
        surface=args.surface,
        suite=args.suite,
        include_variants=not args.representatives,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_results(payload)


if __name__ == "__main__":
    main()
