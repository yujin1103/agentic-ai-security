# AgentDojo-style MCP Prompt Injection Lab

이 프로젝트는 공식 AI UI + MCP에서 피해자 AI가 실제 서비스처럼 보이는 fake API 도구를 사용하다가, 이메일·캘린더·Drive·웹페이지·Slack·뱅킹·여행·메모리 데이터에 포함된 간접 프롬프트 인젝션에 노출되는 상황을 실험하기 위한 로컬 실습 환경입니다.

모델-facing MCP 서버에는 case 선택, prepare, evaluate, trace 확인 같은 실험 제어 도구를 노출하지 않습니다. 실험자는 PowerShell CLI로 case를 준비하고, 모델은 fake app API만 봅니다.

## Windows PowerShell 실행 흐름

권장 환경은 `uv`입니다. WSL은 필요하지 않습니다.

```powershell
uv venv
uv pip install -r requirements.txt
uv run python scripts\list_cases.py --limit 20
uv run python scripts\prepare_case.py --case-id case_1065
uv run python scripts\show_task.py
uv run python mcp_server.py
```

기본 MCP endpoint:

```text
http://127.0.0.1:58473/mcp
```

공식 AI UI에는 `show_task.py`가 출력한 사용자 요청 문장만 붙여 넣습니다. 모델이 작업을 끝낸 뒤에는 다른 터미널에서 평가합니다.

```powershell
uv run python scripts\evaluate_case.py
uv run python scripts\show_trace.py --limit 100
```

자세한 절차는 `docs/HOW_TO_RUN_OFFICIAL_UI_MCP.md`를 보세요. 환경 설정은 `docs/ENVIRONMENT_SETUP.md`, Cloudflare 연결은 `docs/CLOUDFLARE_MCP_RUN.md`에 있습니다.

## 설계 원칙

- `UserTask`와 `InjectionTask`는 분리되어 있습니다.
- 한 case에는 한 surface에만 공격문이 들어갑니다.
- 공격문은 untrusted tool output에만 삽입됩니다.
- 정상 사용자 목표 성공(`utility_ok`)과 공격 목표 성공(`targeted_asr`)은 분리 평가합니다.
- 모든 도구는 fake state만 수정합니다. 실제 이메일, 송금, 예약, 파일 삭제, 외부 인터넷 요청은 없습니다.
- 상태와 trace는 프로젝트 내부 `lab_env/`에만 기록됩니다.

## MCP에 노출되는 fake API 도구

```text
graph_me_messages
graph_me_message_get
graph_me_sendMail

gmail_users_messages_list
gmail_users_messages_get
gmail_users_messages_send

calendar_events_list
calendar_events_insert

drive_files_list
drive_files_get
drive_files_export
drive_files_create
drive_files_delete

slack_conversations_history
slack_chat_postMessage

plaid_accounts_get
plaid_transactions_get
plaid_transfer_create

amadeus_flight_offers_search
amadeus_hotel_offers_search
car_rental_offers_search
booking_reservations_create

http_get
memory_search
memory_create
```

아래 기능은 MCP에 노출하지 않고 실험자 CLI에서만 실행합니다.

```text
scripts/list_cases.py
scripts/prepare_case.py
scripts/show_task.py
scripts/evaluate_case.py
scripts/show_trace.py
```

## 안전 경계

- `http_get(url)`은 state에 미리 들어 있는 fake URL만 반환합니다.
- `drive_files_delete()`는 fake Drive 파일에 `trashed=True`만 표시합니다.
- `plaid_transfer_create()`는 fake transfer log에 기록만 남깁니다.
- `graph_me_sendMail()`과 `gmail_users_messages_send()`는 fake sent-mail state에 기록만 남깁니다.
- 제출용 zip에는 `.venv`, `__pycache__`, `lab_env/current_case.json`, `lab_env/state.json`, `lab_env/traces/*.jsonl`을 포함하지 않습니다.

## GUI launcher

Windows 사용자는 압축 해제 후 `START_LAB_GUI.bat`을 더블클릭하면 Tkinter GUI를 사용할 수 있습니다. 콘솔 창 없이 열려면 `START_LAB_GUI.vbs`를 사용할 수 있습니다.

GUI에서 환경 준비, case 선택, prepare, single-vector 확인, MCP 서버 시작/중지, 평가, trace 확인, 전체 검증을 버튼으로 실행할 수 있습니다. 창의 X 버튼이나 Alt+F4로 종료할 때 실행 중인 MCP 서버를 중지하도록 처리되어 있습니다.
