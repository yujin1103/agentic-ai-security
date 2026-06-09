# 아카이브 (감사 이전 산출물)

이 폴더의 파일들은 2026-06-10 방법론 보강(공통난수 CRN, 전파깊이 조건부 평균, Wilson CI,
relay fidelity, ingest×relay 그리드) **이전**의 결과/로그입니다. 참고용으로만 보존합니다.

- result_20260608_100604.json : (구) 헤드라인. ingest=none. 단, ASR 0.94/0.94/0.95/0.97 의
  방어 간 미세 차이는 d_idx 시드 노이즈 아티팩트였고(현재 CRN 으로 제거), 전파깊이가
  음수(-0.05 등)로 집계되던 버그가 있었음.
- result_20260608_100631.json : ingest=sanitize 라 전 항목 0(비대표 실행). 헤드라인 아님.
- exfil_log.jsonl : 여러 run 이 append 로 누적된 로그(8,705줄). 단일 실험 증거 아님.
  현재는 기본 비기록으로 바뀜.

canonical 결과는 상위 results/ 의 result_*.json(relay 스윕) 과 grid_*.json(2D) 을 보라.
