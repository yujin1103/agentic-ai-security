from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.terminal_ui import bullet, numbered, title, wrapped_value, yn
from app.mcp.admin import admin_get_trace


def _short_json(value, max_len: int = 260) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        text = str(value)
    return wrapped_value(text, max_len)


def print_trace(result: dict) -> None:
    trace = result.get("trace", [])
    print(title("도구 호출 로그"))
    print(bullet("표시 개수", f"{len(trace)}개"))
    if not trace:
        print(bullet("로그", "아직 도구 호출 기록이 없습니다."))
        return
    for i, row in enumerate(trace, start=1):
        tool = row.get("tool") or row.get("tool_name") or row.get("event") or row.get("type") or "unknown"
        print("\n" + numbered(i, str(tool)))
        if row.get("ts"):
            print(bullet("시간", row.get("ts")))
        if row.get("case_id"):
            print(bullet("케이스 ID", row.get("case_id")))
        print(bullet("차단", yn(row.get("blocked"))))
        if "args" in row:
            print(bullet("입력", _short_json(row.get("args"))))
        elif "args_preview" in row:
            print(bullet("입력", wrapped_value(row.get("args_preview"), 260)))
        if row.get("error"):
            print(bullet("오류", row.get("error")))
        if "output_preview" in row:
            print(bullet("출력 요약", wrapped_value(row.get("output_preview"), 260)))


def main() -> None:
    parser = argparse.ArgumentParser(description="사람 전용 도구 호출 로그 확인")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--json", action="store_true", help="기계 처리용 JSON 출력")
    args = parser.parse_args()
    result = admin_get_trace(args.limit)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print_trace(result)


if __name__ == "__main__":
    main()
