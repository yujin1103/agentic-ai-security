from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.terminal_ui import bullet, ko_surface, ko_suite, ko_task, numbered, title, wrapped_value
from app.envs.seeder import prepare_case


def print_prepared(result: dict) -> None:
    print(title("케이스 준비 완료"))
    print(numbered(1, "선택한 케이스"))
    print(bullet("케이스 ID", result.get("case_id")))
    print(bullet("스위트", ko_suite(result.get("suite"))))
    print(bullet("사용자 작업 ID", result.get("user_task_id")))
    print(bullet("작업 요약", ko_task(result.get("user_task_id"))))

    print(numbered(2, "인젝션 위치"))
    print(bullet("오염된 위치", f"{ko_surface(result.get('surface'))} 인젝션"))
    print(bullet("단일 위치 통제", "켜짐" if result.get("single_vector_control") else "꺼짐"))
    print(bullet("깨끗하게 비운 나머지 위치 수", result.get("clean_surfaces_count")))

    print(numbered(3, "공식 AI UI에 넣을 사용자 요청"))
    print(bullet("작업 요약", ko_task(result.get("user_task_id"))))
    print(bullet("복사용 원문", wrapped_value(result.get("user_prompt", ""), 1000)))
    print("\n주의: 위 사용자 요청만 공식 AI UI에 넣고, 이 준비 정보는 넣지 마세요.")


def main() -> None:
    parser = argparse.ArgumentParser(description="사람 전용 준비 명령입니다. 선택한 case의 fake 환경을 lab_env에 씁니다.")
    parser.add_argument("--case-id", required=True, help="scripts/list_cases.py에서 고른 case_0001 같은 ID")
    parser.add_argument("--json", action="store_true", help="기계 처리용 JSON 출력")
    args = parser.parse_args()
    result = prepare_case(args.case_id)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print_prepared(result)


if __name__ == "__main__":
    main()
