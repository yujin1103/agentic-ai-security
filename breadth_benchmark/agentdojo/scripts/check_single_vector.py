from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.json_store import get_current_case, get_state
from app.core.terminal_ui import bullet, ko_surface, none_text, numbered, title, yn
from app.envs.seeder import prepare_case
from app.envs.base_state import PLACEHOLDERS


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _collect_strings(obj: Any) -> list[str]:
    """Collect raw model-facing strings without JSON escaping.

    Multiline attack families contain real newlines. json.dumps() turns those
    into escaped \n sequences, which made single-vector checks miss attacks
    that were actually present in state.
    """
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, list):
        out: list[str] = []
        for item in obj:
            out.extend(_collect_strings(item))
        return out
    if isinstance(obj, dict):
        out: list[str] = []
        for value in obj.values():
            out.extend(_collect_strings(value))
        return out
    return []


def _surface_text(obj: Any) -> str:
    return "\n".join(_collect_strings(obj))


def surface_texts(state: dict[str, Any]) -> dict[str, str]:
    return {
        "mail": _surface_text(state.get("mail", {})),
        "calendar": _surface_text(state.get("calendar", {})),
        "drive": _surface_text(state.get("drive", {})),
        "web": _surface_text(state.get("web", {})),
        "slack": _surface_text(state.get("slack", {})),
        "banking": _surface_text(state.get("banking", {})),
        "travel": _surface_text(state.get("travel", {})),
        "memory": _surface_text(state.get("memory", {})),
    }


def build_result(case_id: str) -> dict[str, Any]:
    prepared = prepare_case(case_id)
    current = get_current_case()
    state = get_state()
    attack = current.get("attack_text_preview", "")
    needle = attack[:80]
    texts = surface_texts(state)
    hits = [surface for surface, text in texts.items() if needle and needle in text]
    remaining_text = _surface_text(state)
    remaining_placeholders = [name for name, token in PLACEHOLDERS.items() if token in remaining_text]
    return {
        "prepared": prepared,
        "expected_surface_label": current.get("injection_surface"),
        "surfaces_containing_attack_text": hits,
        "hit_count": len(hits),
        "remaining_placeholders": remaining_placeholders,
        "single_vector_ok": len(hits) == 1 and not remaining_placeholders,
    }


def print_result(result: dict[str, Any]) -> None:
    prepared = result.get("prepared", {})
    hits = result.get("surfaces_containing_attack_text", [])
    placeholders = result.get("remaining_placeholders", [])
    print(title("단일 인젝션 위치 검사"))
    print(numbered(1, "검사 대상"))
    print(bullet("케이스 ID", prepared.get("case_id")))
    expected = prepared.get("surface") or (hits[0] if hits else "")
    print(bullet("예상 위치", f"{ko_surface(expected)} 인젝션" if expected else result.get("expected_surface_label")))

    print(numbered(2, "검사 결과"))
    print(bullet("통과", yn(result.get("single_vector_ok"))))
    print(bullet("공격문이 발견된 위치", none_text([ko_surface(x) for x in hits])))
    print(bullet("발견 위치 수", result.get("hit_count")))
    print(bullet("남은 placeholder", none_text(placeholders)))

    if result.get("single_vector_ok"):
        print("\n결론: 이 case는 한 위치에만 인젝션이 들어간 상태입니다.")
    else:
        print("\n결론: 이 case는 단일 위치 통제에 실패했습니다. prepare/check 로직을 확인하세요.")


def main() -> None:
    parser = argparse.ArgumentParser(description="선택한 case가 한 surface에만 공격문을 갖는지 확인합니다.")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--json", action="store_true", help="기계 처리용 JSON 출력")
    args = parser.parse_args()
    result = build_result(args.case_id)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print_result(result)


if __name__ == "__main__":
    main()
