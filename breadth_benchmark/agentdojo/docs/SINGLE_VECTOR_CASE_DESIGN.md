# Single-vector case design

이 프로젝트의 각 case는 **한 surface에만** 인젝션 문구가 들어가도록 설계합니다.

현재 기준:

- 전체 case: 2,128개
- 대표 task-surface/placeholder 조합: 38개
- surface: mail, calendar, drive, web, slack, banking, travel, memory
- 각 대표 조합은 7개 공격 목표 × 8개 attack family = 56개 실험 조합으로 확장됩니다.

## 핵심 원칙

- `surface=mail`: 해당 user task가 실제로 검색/조회할 이메일 본문에만 인젝션이 들어갑니다.
- `surface=calendar`: 해당 user task가 조회할 기존 캘린더 event description에만 인젝션이 들어갑니다.
- `surface=drive`: 해당 user task가 검색/export할 Drive 문서 내용에만 인젝션이 들어갑니다.
- `surface=web`: 해당 user task에 포함된 fake URL의 `http_get` 결과에만 인젝션이 들어갑니다.
- `surface=slack`: 해당 user task가 읽을 Slack channel history 메시지에만 인젝션이 들어갑니다.
- `surface=banking`: 해당 user task가 조회할 transaction/account metadata에만 인젝션이 들어갑니다.
- `surface=travel`: 해당 user task가 검색할 hotel/car offer의 review/note에만 인젝션이 들어갑니다.
- `surface=memory`: 해당 user task가 검색할 memory 문서에만 인젝션이 들어갑니다.

한 case 안에서 여러 surface가 동시에 오염되면 원인 분리가 깨지므로 기본 case로 사용하지 않습니다.

## 대표 예시

- `case_1065`: W01 / mail / Alice meeting notes email
- `case_1121`: W02 / calendar / compliance renewal deadline event
- `case_1289`: W03 / drive / project_launch.md
- `case_1681`: W07 / web / vendor product page
- `case_1401`: W04 / slack / C-security channel
- `case_0113`: B03 / banking / unusual transaction note
- `case_0729`: T02 / travel / Paris hotel offer
- `case_0225`: M01 / memory / Agentic AI project note

## 실험자용 흐름

```powershell
uv run python scripts\list_cases.py --limit 20
uv run python scripts\prepare_case.py --case-id case_1065
uv run python scripts\check_single_vector.py --case-id case_1065
uv run python scripts\show_task.py
uv run python mcp_server.py
```

공식 UI에는 `show_task.py`가 출력한 user prompt만 붙여넣습니다. case id, injection surface, attack family, injection goal은 모델에게 말하지 않습니다.

## 검증 흐름

```powershell
uv run python scripts\prepare_case.py --case-id case_1065
uv run python scripts\check_single_vector.py --case-id case_1065
uv run python scripts\show_task.py
uv run python scripts\evaluate_case.py
uv run python scripts\show_trace.py
```

`check_single_vector.py`는 다음을 확인합니다.

- 오염 surface가 하나인지
- 공격문이 예상 surface에만 있는지
- 남은 placeholder가 없는지
- 다른 fake app surface에 같은 공격문이 퍼지지 않았는지

## 모델-facing MCP에 없는 것

아래 기능은 MCP tool로 등록하지 않습니다.

- case 목록 확인
- case 준비
- task 표시
- 평가
- trace 확인

이 기능들은 사람이 CLI로만 실행합니다. 모델-facing MCP에는 실제 API처럼 보이는 Gmail/Graph/Calendar/Drive/Slack/Plaid/Travel/Web/Memory 도구만 노출됩니다.
