from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.terminal_ui import bullet, ko_surface, ko_suite, ko_task, numbered, title, wrapped_value
from app.runner.case_manager import list_cases


def _readable_sort_key(row: dict) -> tuple[str, str, str, str]:
    return (
        ko_surface(str(row.get("surface", ""))),
        ko_suite(str(row.get("suite", ""))),
        str(row.get("user_task_id", "")),
        str(row.get("case_id", "")),
    )


def _collapse_variants(rows: list[dict]) -> list[dict]:
    """Show one readable representative per user task and injection surface."""
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        key = (
            str(row.get("surface", "unknown")),
            str(row.get("user_task_id", "unknown")),
            str(row.get("injection_surface", "unknown")),
        )
        grouped[key].append(row)

    collapsed: list[dict] = []
    for (_surface, _task_id, _injection_surface), variants in grouped.items():
        variants = sorted(variants, key=lambda r: str(r.get("case_id", "")))
        representative = dict(variants[0])
        representative["variant_count"] = len(variants)
        representative["variant_case_ids_preview"] = [str(v.get("case_id")) for v in variants[:5]]
        representative["variant_summaries_preview"] = [str(v.get("variant_summary", "")) for v in variants[:5]]
        collapsed.append(representative)

    return sorted(collapsed, key=_readable_sort_key)


def _surface_balanced(rows: list[dict]) -> list[dict]:
    """Round-robin surfaces so the default first page does not look duplicated."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in sorted(rows, key=_readable_sort_key):
        buckets[str(row.get("surface", "unknown"))].append(row)

    surface_order = sorted(buckets, key=lambda s: ko_surface(s))
    balanced: list[dict] = []
    while any(buckets.values()):
        for surface in surface_order:
            if buckets[surface]:
                balanced.append(buckets[surface].pop(0))
    return balanced


def print_cases(rows: list[dict], *, suite: str, surface: str, limit: int, all_variants: bool) -> None:
    print(title("케이스 목록"))
    print(bullet("필터", f"스위트={suite or '전체'}, 위치={ko_surface(surface) if surface else '전체'}, 최대 {limit}개"))
    print(bullet("표시 방식", "모든 실험 조합 표시: 같은 작업이 목표/표현 방식별로 반복됨" if all_variants else "대표 task-surface 조합 중심 표시"))
    print(bullet("표시 개수", f"{len(rows)}개"))
    if not rows:
        print(bullet("결과", "조건에 맞는 케이스가 없습니다."))
        return

    for idx, row in enumerate(rows, start=1):
        surface_key = str(row.get("surface", "unknown"))
        case_id = row.get("case_id")
        suite_ko = ko_suite(row.get("suite"))
        task_id = row.get("user_task_id")
        print("\n" + numbered(idx, f"{ko_surface(surface_key)} 인젝션 | {case_id} | {suite_ko} | {task_id}"))
        print(bullet("작업 요약", ko_task(task_id, wrapped_value(row.get("user_task", ""), 120)), indent=2))
        if all_variants:
            print(bullet("실험 조합", wrapped_value(str(row.get("variant_summary", "")), 120), indent=2))
            print(bullet("목표", wrapped_value(str(row.get("attack_goal_summary", "")), 140), indent=2))
            print(bullet("표현 방식", wrapped_value(str(row.get("attack_family_display", "")), 120), indent=2))
        else:
            previews = row.get("variant_summaries_preview", []) or []
            preview_text = "; ".join(previews[:3])
            suffix = " ..." if len(previews) > 3 else ""
            print(
                bullet(
                    "동일 작업의 다른 실험 조합",
                    f"{row.get('variant_count', 1)}개, 현재 목록에는 대표 1개만 표시" + (f" — 예: {preview_text}{suffix}" if preview_text else ""),
                    indent=2,
                )
            )
        print(bullet("오염 위치", f"{ko_surface(surface_key)} 데이터에만 인젝션 삽입", indent=2))
        print(bullet("세부 위치", wrapped_value(row.get("injection_surface", ""), 180), indent=2))
        print(bullet("복사용 원문", wrapped_value(row.get("user_task", ""), 180), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="사람이 실험 전에 읽는 케이스 목록입니다. 모델에게 보여주지 않습니다.")
    parser.add_argument("--suite", default="")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--surface", default="", help="mail, calendar, drive, web, slack, banking, travel, memory")
    parser.add_argument("--all-variants", action="store_true", help="같은 작업의 공격 조합까지 모두 표시")
    parser.add_argument("--json", action="store_true", help="기계 처리용 JSON 출력")
    args = parser.parse_args()

    raw_rows = list_cases(args.suite or None, None, args.surface or None)
    rows = raw_rows if args.all_variants else _collapse_variants(raw_rows)

    if not args.surface:
        rows = _surface_balanced(rows)
    elif not args.all_variants:
        rows = sorted(rows, key=_readable_sort_key)

    rows = rows[: args.limit] if args.limit else rows

    if args.json:
        print(json.dumps({"cases": rows}, ensure_ascii=False, indent=2))
        return
    print_cases(rows, suite=args.suite, surface=args.surface, limit=args.limit, all_variants=args.all_variants)


if __name__ == "__main__":
    main()
