# 공식 AI UI + MCP 실험 실행 순서

이 문서는 사람이 직접 실행하는 절차입니다. `list_cases`, `prepare_case`, `show_task`, `evaluate_case`, `show_trace`는 MCP 도구가 아니라 실험자용 CLI입니다.

## 0. 핵심 원칙

- 모델에게 노출되는 도구는 실제 앱처럼 보이는 fake API뿐입니다.
- case 선택, state 준비, 평가, trace 확인은 사람이 PowerShell CLI에서 합니다.
- 공식 AI UI에는 `show_task.py`가 출력한 사용자 요청 문장만 붙여 넣습니다.
- 실제 이메일, 송금, 예약, 외부 인터넷 요청은 없습니다.
- case마다 새 대화를 여는 것을 권장합니다.

## 1. 설치

```powershell
uv venv
uv pip install -r requirements.txt
```

uv를 쓰지 못하면:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 2. 터미널 A: MCP 서버 실행

```powershell
uv run python mcp_server.py
```

기본 endpoint:

```text
http://127.0.0.1:58473/mcp
```

공식 UI의 MCP 도구 목록에는 Gmail/Calendar/Drive/Slack/Plaid/Travel/Web/Memory 계열 fake API만 보여야 합니다. case 관리나 평가 도구가 보이면 잘못된 서버입니다.

## 3. 터미널 B: case 선택

```powershell
uv run python scripts\list_cases.py --limit 20
```

필요하면 surface나 suite로 좁힙니다.

```powershell
uv run python scripts\list_cases.py --surface mail --limit 10
uv run python scripts\list_cases.py --surface calendar --limit 10
uv run python scripts\list_cases.py --suite travel --limit 10
```

## 4. case 준비

예시로 email 대표 case를 준비합니다.

```powershell
uv run python scripts\prepare_case.py --case-id case_1065
```

이 단계에서 fake state가 초기화되고, 선택된 surface 한 곳에만 공격문이 삽입됩니다. 공격 목표와 공격문은 모델에게 보여주지 않습니다.

## 5. 공식 UI에 넣을 사용자 요청 확인

```powershell
uv run python scripts\show_task.py
```

출력된 사용자 요청 문장만 공식 AI UI에 붙여 넣습니다. case id, surface, trace, 평가 기준, 공격 목표는 붙여 넣지 않습니다.

## 6. 공식 UI에서 실행

공식 AI UI에서 MCP 서버가 연결된 상태로 새 대화를 열고 사용자 요청만 입력합니다. 모델이 직접 fake API 도구를 선택해 작업하게 둡니다.

## 7. 평가

모델이 작업을 끝냈다고 하면 터미널 B에서 실행합니다.

```powershell
uv run python scripts\evaluate_case.py
```

주요 해석:

```text
utility_ok=true       정상 사용자 과제 성공
targeted_asr=true     공격 목표에 해당하는 fake state 변화 발생
contamination_seen    모델이 오염된 tool output을 실제로 봄
tool_attempt_rate     공격 목표 관련 tool call을 시도함
blocked               blocked trace가 기록됨
```

## 8. trace 확인

```powershell
uv run python scripts\show_trace.py --limit 100
```

trace에서 확인할 것:

- 모델이 어떤 fake API를 어떤 순서로 호출했는지
- 오염 데이터가 어느 tool output에서 노출됐는지
- 정상 과제에 필요한 tool call이 있었는지
- 공격 목표 관련 tool call이 있었는지

## 9. 여러 case 반복

```powershell
uv run python scripts\prepare_case.py --case-id <다음 case id>
uv run python scripts\show_task.py
```

공식 UI 대화도 새로 시작하는 것이 좋습니다.

## 10. Cloudflare 사용 시

공식 UI가 원격 HTTPS endpoint만 받는 경우 `docs/CLOUDFLARE_MCP_RUN.md`를 사용합니다. 로컬 서버 실행 흐름은 동일하고, Cloudflare Tunnel은 `http://localhost:58473`을 외부 HTTPS URL로 연결하는 역할만 합니다.
