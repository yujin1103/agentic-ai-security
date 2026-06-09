# Agentic AI 프롬프트 인젝션 — 통합 프로젝트

PPT 「인공지능 보안 제안발표」(Agentic AI 프롬프트 인젝션)를 **"조사·분류형 서베이"에서
"재현 가능한 red-team 측정"** 으로 끌어올린 통합 프로젝트입니다. 두 갈래로 구성됩니다.

> **점검 대비 핵심 문서:** [`PROFESSOR_REVIEW_PREP.md`](./PROFESSOR_REVIEW_PREP.md) — 예상 질문·정직한
> 답변·우리가 고친 것·한계·증거 지도. **점검 전 이 문서부터 읽으세요.**

---

## 폴더 구조

```
agentic-ai-security/
  README.md                  (이 파일 — 통합·용어집)
  PROFESSOR_REVIEW_PREP.md   (점검 대비 Q&A·한계·증거지도)
  인공지능 보안 제안발표.pptx

  breadth_benchmark/         ← 넓이: 단일 에이전트 벤치마크 (팀원)
    agentdojo/   client/

  depth_labs/                ← 깊이: 멀티에이전트/세션/모달 + 방어 정량화 (본인)
    agent_injection_lab/        멀티에이전트 체인 전파 (공간축)
    memory_poisoning_lab/       메모리·컨텍스트 오염 (시간축, cross-session)
    multimodal_injection_lab/   멀티모달 인젝션 채널 (이미지→텍스트)
    nanoclaw_attack_lab/        실제 프레임워크 공격 + 호스트 방어 게이트
    nanoclaw/                   공격 대상(third-party 멀티에이전트 프레임워크)
    nanoclaw_setup/             라이브 실험용 격리 VM 셋업
```

## 구성 (한눈에)

| 경로 | 무엇 | PPT 대응 | 안전 등급 |
|---|---|---|---|
| `breadth_benchmark/` | **단일 에이전트 넓이 벤치마크**(AgentDojo 스타일, 8 surface×8 family×7 goal=2128 case, 공식 UI+MCP) | 슬라이드 4 개념, 시나리오 ①② | 구조적 mock |
| `depth_labs/agent_injection_lab/` | **멀티에이전트 체인 전파**(공간축). ingest/relay 두 경계 방어, IR/깊이/ASR/봉쇄/fidelity, ingest×relay 2D 그리드 | 시나리오 ③, 슬라이드 7 | 구조적 mock |
| `depth_labs/memory_poisoning_lab/` | **메모리·컨텍스트 오염**(시간축). 세션 A 심기→세션 B 발동, write/read 경계 방어 | 시나리오 ④ | 구조적 mock |
| `depth_labs/multimodal_injection_lab/` | **멀티모달 인젝션 채널**(이미지→OCR/EXIF/alt-text→텍스트). cross-channel 일관성 방어 | 슬라이드 4 멀티모달 | 구조적 mock |
| `depth_labs/nanoclaw_attack_lab/` | **실제 멀티에이전트 프레임워크 공격**. inbound.db 격리 주입→시크릿 exfil, 호스트 review_gate 방어(+적응형 평가) | 시나리오 ①②, 슬라이드 5 | mock(offline)+라이브(실egress) |

> **역할 분담(한 문장):** breadth=넓이(단일 에이전트, 2128 case), depth=깊이(멀티에이전트/세션/
> 모달 + 방어 정량화). **중복이 아니라 분담**이다.

---

## 정직성 스탠스 (반드시 숙지)

1. **mock 백엔드 수치는 측정이 아니라 가정한 파라미터의 시뮬레이션이다.** 각 랩 출력에
   `[mock=가정 파라미터 — 측정값 아님]` 라벨이 박혀 있다. 정량적 취약성 주장은 실모델
   (`--backend ollama`) 결과에서만 한다. **세 depth 랩을 2개 실모델로 실측**
   (`*/results/*_ollama_*.json`): **취약성은 모델 크기에 강하게 의존** —
   `llama3.2`(3B)는 단발 인젝션에 굴복(ASR 100%)하지만 `llama3.1`(8B)은 **노출돼도 전부 거부
   (ASR 0%)**. mock의 단일 가정(0.95)은 작은 모델엔 과소·큰 모델엔 과대로 **양방향 반증**된다 —
   "측정 > 가정"의 결정적 증거. (n≤8 소표본·대형/다기종은 future work.)
2. **새 현상의 발견이 아니다.** 멀티에이전트 자기전파는 선행연구(Prompt Infection 2410.07283,
   Agent Smith 2402.08567)가 이미 보였다. 기여는 **재현 가능한 측정 도구화 + 경계 분해 +
   cross-session 실증 + 방어 trade-off 정량화 + 실모델로 가정 반증**이다.
3. 모든 도구는 mock(라이브 nanoclaw 제외), 더미 시크릿, `attacker.invalid`/로컬 리스너만 사용한다.

---

## 빠른 실행 (모두 표준 라이브러리, `py -3`)

```powershell
# 멀티에이전트 전파
cd E:\agentic-ai-security\depth_labs\agent_injection_lab
py -3 run.py --agents 6 --trials 200 --show-chain   # relay 스윕(mock)
py -3 run.py --grid --agents 6 --trials 200         # ingest×relay 2D(mock)
py -3 run.py --backend ollama --model llama3.2 --agents 4 --trials 6   # 실모델

# 메모리 cross-session 오염
cd E:\agentic-ai-security\depth_labs\memory_poisoning_lab
py -3 run.py --trials 200 ; py -3 run.py --demo

# 멀티모달 채널
cd E:\agentic-ai-security\depth_labs\multimodal_injection_lab
py -3 run.py --trials 200 ; py -3 run.py --demo

# nanoclaw 게이트(자기평가 + 적응형 held-out)
cd E:\agentic-ai-security\depth_labs\nanoclaw_attack_lab
py -3 run_demo.py ; py -3 run_demo.py --adaptive
```
실모델 경로는 **Ollama(로컬, API 키 불필요)**. `ollama pull llama3.2` 후 위 `--backend ollama` 사용.
Windows에서 출력을 다른 도구로 **캡처**할 땐 `PYTHONUTF8=1` 설정(한글/이모지 디코드).

---

## 근거 문헌
- Greshake et al. 2023, *Not what you've signed up for* (indirect injection), arXiv:2302.12173
- *Prompt Infection: LLM-to-LLM Prompt Injection within Multi-Agent Systems*, arXiv:2410.07283
- *Agent Smith / Infectious Jailbreak*, arXiv:2402.08567
- Microsoft *Spotlighting* (data/instruction separation)

## 범위 밖 (한계)
- 실모델은 단일 소형 모델(llama3.2 3B)·소표본(n≤8) — 대형/다기종·대표본은 future work · 적응형
  공격 전면 스윕 · 멀티모달은 채널만(실제 VLM 미측정) · 라이브 안전은 격리 의존. 자세한 한계와
  답변은 `PROFESSOR_REVIEW_PREP.md` §4 참조.
