# Cloudflare Tunnel로 공식 UI에 MCP 연결하기

로컬 MCP endpoint를 공식 UI에서 접근 가능한 HTTPS URL로 연결해야 할 때만 사용합니다. 기본 로컬 실습은 `http://127.0.0.1:58473/mcp`로 충분합니다.

## 1. Python dependency 설치

```powershell
uv venv
uv pip install -r requirements.txt
```

`cloudflared`도 설치되어 있어야 합니다.

```powershell
cloudflared --version
```

## 2. 터미널 A: MCP 서버 실행

```powershell
uv run python mcp_server.py
```

또는 helper:

```powershell
.\scripts\run_server_uv.ps1
```

## 3. 터미널 B: Cloudflare Quick Tunnel 실행

```powershell
cloudflared tunnel --url http://localhost:58473
```

또는 helper:

```powershell
.\scripts\run_cloudflare_quick_tunnel.ps1
```

Cloudflare가 출력한 URL 뒤에 `/mcp`를 붙여 공식 UI remote MCP endpoint로 사용합니다.

```text
https://something-random.trycloudflare.com/mcp
```

## 4. case 준비와 평가는 별도 CLI에서 수행

```powershell
uv run python scripts\list_cases.py --limit 20
uv run python scripts\prepare_case.py --case-id case_1065
uv run python scripts\show_task.py
```

`show_task.py`가 출력한 사용자 요청 문장만 공식 UI에 붙여 넣습니다.

모델이 작업을 끝내면:

```powershell
uv run python scripts\evaluate_case.py
uv run python scripts\show_trace.py --limit 100
```

## 5. 주의

- Quick Tunnel은 개발/테스트용 임시 URL입니다.
- Cloudflare는 case 선택이나 평가를 대신하지 않습니다.
- case 관리 스크립트를 MCP tool로 노출하지 않습니다.
- 실제 이메일/송금/예약 계정을 연결하지 않습니다.
