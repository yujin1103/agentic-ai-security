from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.terminal_ui import bullet, ko_suite, numbered, title, yn
from app.mcp.admin import admin_evaluate_case


def print_eval(result: dict) -> None:
    if "error" in result:
        print(title("평가 결과"))
        print(bullet("상태", result["error"]))
        return

    print(title("평가 결과"))
    print(numbered(1, "성공 여부"))
    print(bullet("정상 사용자 작업 성공", yn(result.get("utility_ok"))))
    print(bullet("공격 목표 성공", yn(result.get("targeted_asr"))))
    print(bullet("정상만 성공하고 공격은 실패", yn(result.get("utility_under_attack"))))

    print(numbered(2, "노출/시도/차단"))
    print(bullet("오염된 도구 출력 노출", yn(result.get("contamination_seen"))))
    print(bullet("공격 목표 도구 시도", yn(result.get("tool_attempt_rate"))))
    print(bullet("차단 발생", yn(result.get("block_rate"))))
    print(bullet("도구 호출 수", result.get("tool_call_count")))

    print(numbered(3, "참고"))
    print(bullet("스위트", ko_suite(result.get("suite"))))
    print(bullet("메모", result.get("notes")))


def main() -> None:
    try:
        result = admin_evaluate_case()
    except RuntimeError as exc:
        result = {"error": str(exc)}
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print_eval(result)


if __name__ == "__main__":
    main()
