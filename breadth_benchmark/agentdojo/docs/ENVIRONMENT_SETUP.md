# Python 환경 설정

Windows PowerShell 기준입니다. WSL은 필요하지 않습니다. 모든 명령은 압축을 푼 프로젝트 루트에서 실행합니다.

## 1. uv 권장

```powershell
uv venv
uv pip install -r requirements.txt
```

MCP 서버 실행:

```powershell
uv run python mcp_server.py
```

case 관리 CLI 실행:

```powershell
uv run python scripts\list_cases.py --limit 20
uv run python scripts\prepare_case.py --case-id case_1065
uv run python scripts\show_task.py
uv run python scripts\evaluate_case.py
uv run python scripts\show_trace.py --limit 100
```

## 2. venv fallback

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

MCP 서버 실행:

```powershell
.\.venv\Scripts\python.exe mcp_server.py
```

case 관리 CLI 실행:

```powershell
.\.venv\Scripts\python.exe scripts\list_cases.py --limit 20
.\.venv\Scripts\python.exe scripts\prepare_case.py --case-id case_1065
.\.venv\Scripts\python.exe scripts\show_task.py
.\.venv\Scripts\python.exe scripts\evaluate_case.py
.\.venv\Scripts\python.exe scripts\show_trace.py --limit 100
```

## 3. 기본 MCP endpoint

```text
http://127.0.0.1:58473/mcp
```

원격 HTTPS URL이 필요한 공식 UI에서는 `docs/CLOUDFLARE_MCP_RUN.md`의 Cloudflare Tunnel 절차를 사용합니다.

## 4. 실험 실행 순서

터미널 A:

```powershell
uv run python mcp_server.py
```

터미널 B:

```powershell
uv run python scripts\list_cases.py --limit 20
uv run python scripts\prepare_case.py --case-id case_1065
uv run python scripts\show_task.py
```

`show_task.py`가 출력한 사용자 요청만 공식 AI UI에 붙여 넣습니다. AI가 MCP 도구를 사용한 뒤:

```powershell
uv run python scripts\evaluate_case.py
uv run python scripts\show_trace.py --limit 100
```

## 5. 주의

- zip 안에서 직접 실행하지 말고 압축을 푼 폴더에서 실행합니다.
- dependency 파일은 `requirements.txt` 하나만 사용합니다.
- 실제 이메일, 실제 송금, 실제 예약, 실제 인터넷 요청은 실행되지 않습니다.
- 한 case가 끝난 뒤 다른 case를 실행할 때는 `prepare_case.py`를 다시 실행하고 공식 UI 대화도 새로 시작하는 것을 권장합니다.
