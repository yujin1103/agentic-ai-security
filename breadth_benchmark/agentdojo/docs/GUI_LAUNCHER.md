# GUI Launcher

Windows PowerShell 명령을 직접 입력하지 않고 실습을 진행하기 위한 사람용 로컬 GUI입니다. 피해자 AI에게 노출되는 MCP 도구가 아니며, `mcp_server.py`에 등록되지 않습니다.

## 실행

압축을 푼 뒤 프로젝트 루트에서 아래 파일 중 하나를 실행합니다.

- `START_LAB_GUI.bat`: 콘솔 로그가 보이는 실행 방식
- `START_LAB_GUI.vbs`: 콘솔 창 없이 실행

## 주요 버튼

- 환경 준비: `uv venv`와 `uv pip install -r requirements.txt` 실행
- case 목록 새로고침: 대표 case 목록 로드
- 선택 case 준비: `prepare_case.py` 실행
- single-vector 확인: `check_single_vector.py` 실행
- UI용 문장 보기/복사: 공식 UI에 넣을 user task를 클립보드에 복사
- MCP 서버 시작/중지: `uv run python mcp_server.py` 실행/종료
- 평가 실행: `evaluate_case.py` 실행
- Trace 보기: `show_trace.py` 실행
- 전체 검증: `verify_all_cases.py` 실행
- lab_env 정리: 현재 case/state/trace 파일 삭제

## 종료 처리

GUI 창의 X 버튼, Alt+F4, 종료 버튼으로 닫으면 실행 중인 MCP 서버를 중지할지 확인하고 종료합니다. 서버가 정상 종료되지 않으면 Windows에서는 `taskkill /T /F`로 프로세스 트리 종료를 시도합니다.

컴퓨터 강제 전원 차단, 작업 관리자에서 즉시 프로세스 종료 같은 경우는 어떤 GUI도 Python cleanup 코드를 보장 실행할 수 없습니다. 다만 일반 종료, Alt+F4, 신호 기반 종료는 best-effort cleanup이 들어 있습니다.
