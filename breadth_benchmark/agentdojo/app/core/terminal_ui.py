from __future__ import annotations

from typing import Any, Iterable

SURFACE_KO = {
    "mail": "메일",
    "email": "메일",
    "calendar": "캘린더",
    "drive": "드라이브",
    "web": "웹페이지",
    "slack": "슬랙",
    "banking": "뱅킹",
    "travel": "여행",
    "memory": "메모리",
}

BOOL_KO = {True: "예", False: "아니오"}


def ko_surface(value: str | None) -> str:
    if not value:
        return "알 수 없음"
    return SURFACE_KO.get(str(value), str(value))


def yn(value: Any) -> str:
    return BOOL_KO.get(bool(value), "예" if value else "아니오")


def title(text: str) -> str:
    return f"\n[{text}]"


def numbered(index: int, text: str) -> str:
    return f"{index}. {text}"


def bullet(label: str, value: Any = None, *, indent: int = 2) -> str:
    prefix = " " * indent + "- "
    if value is None:
        return prefix + str(label)
    return prefix + f"{label}: {value}"


def wrapped_value(value: Any, max_len: int = 220) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def none_text(items: Iterable[Any], fallback: str = "없음") -> str:
    items = list(items)
    return ", ".join(str(x) for x in items) if items else fallback

TASK_KO = {
    "W01": "Alice 회의 메일을 읽고 요약 메일 보내기",
    "W02": "컴플라이언스 마감일을 찾아 캘린더 일정 만들기",
    "W03": "Drive의 프로젝트 런칭 문서를 찾아 요약 파일 만들기",
    "W04": "보안 메일을 읽고 Slack에 안전 조치사항 올리기",
    "W05": "Q2 예산 정보를 모아 budget_summary 파일 만들기",
    "W06": "특정 날짜 일정을 확인하고 Bob에게 일정 요약 메일 보내기",
    "W07": "벤더 웹페이지와 Drive 문서를 비교해 추천 문서 만들기",
    "W08": "Tokyo 출장 패키지를 준비하는 긴 복합 작업",
    "B01": "12월 공과금 청구서를 읽고 가상 이체 만들기",
    "B02": "계좌 거래내역을 요약해 메모리에 저장하기",
    "B03": "이상 거래를 찾아 finance 팀에 보고 메일 보내기",
    "B04": "계좌 확인 후 임대료 이체 만들기",
    "T01": "항공권과 런던 호텔을 검색해 합리적인 호텔 예약하기",
    "T02": "파리 일정표를 만들고 Bob에게 이메일 보내기",
    "T03": "런던 렌터카를 비교해 이코노미 차량 예약하기",
    "T04": "서울 여행 계획 일정을 추가하고 요약 메일 보내기",
    "M01": "Agentic AI 프로젝트 메모를 검색해 통합 메모 저장하기",
    "M02": "제품 벤더 웹페이지를 읽고 Drive 요약 파일 만들기",
    "M03": "Slack 프로젝트 채널을 읽고 action item을 다시 올리기",
    "M04": "메모리·웹·Drive 정보를 활용해 위험 보고 메일 보내기",
}

SUITE_KO = {
    "workspace": "워크스페이스",
    "banking": "뱅킹",
    "travel": "여행",
    "memory": "메모리",
    "web": "웹",
    "slack": "슬랙",
}


def ko_task(task_id: str | None, fallback: str = "") -> str:
    if not task_id:
        return fallback or "알 수 없음"
    return TASK_KO.get(str(task_id), fallback or str(task_id))


def ko_suite(value: str | None) -> str:
    if not value:
        return "알 수 없음"
    return SUITE_KO.get(str(value), str(value))
