from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.terminal_ui import bullet, ko_suite, ko_task, numbered, title
from app.mcp.admin import admin_current_task


def main() -> None:
    task = admin_current_task()
    if "error" in task:
        print(title("현재 사용자 요청"))
        print(bullet("상태", task["error"]))
        return

    if "--json" in sys.argv:
        print(json.dumps(task, ensure_ascii=False, indent=2))
        return

    prompt = task.get("user_prompt", "")
    print(title("공식 AI UI에 입력할 사용자 요청"))
    print(numbered(1, "준비된 케이스 정보"))
    print(bullet("케이스 ID", task.get("case_id")))
    print(bullet("스위트", ko_suite(task.get("suite"))))
    print(bullet("사용자 작업", f"{task.get('user_task_id')} - {ko_task(task.get('user_task_id'))}"))

    print(numbered(2, "복사할 문장"))
    print("----- 복사 시작 -----")
    print(prompt)
    print("----- 복사 끝 -----")
    print("위 복사 구간 안의 문장만 공식 AI UI에 입력하세요.")


if __name__ == "__main__":
    main()
