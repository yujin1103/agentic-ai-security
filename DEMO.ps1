<#
  발표용 원클릭 데모 — Agentic AI 프롬프트 인젝션 통합 프로젝트
  교수님 앞에서 Enter 만 누르며 ①~⑥ 순서대로 시연하도록 만든 스크립트.

  사용:
    powershell -ExecutionPolicy Bypass -File DEMO.ps1        # 일시정지하며 진행(발표용)
    DEMO.ps1 -NoPause                                        # 멈춤 없이 한 번에
    DEMO.ps1 -Quick                                          # mock 데모만(실모델 ⑥ 생략, 즉시)
    DEMO.ps1 -Trials 5                                        # 실모델 trial 수 조정
  (더블클릭은 DEMO.bat 사용)
#>
param(
  [switch]$Quick,           # mock 만(실모델 단계 생략)
  [switch]$NoPause,         # 단계 사이 멈추지 않음
  [int]$Trials = 3,         # 실모델(ollama) trial 수 — 라이브용으로 작게
  [int]$MockTrials = 200    # mock trial 수
)

$ErrorActionPreference = 'Continue'
$env:PYTHONUTF8 = 1
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$root  = $PSScriptRoot
$depth = Join-Path $root 'depth_labs'

function Pause-Step {
  if (-not $NoPause) { [void](Read-Host "`n  --- Enter 를 누르면 다음 단계로 ---") }
}
function Header($n, $title, $msg) {
  Write-Host ''
  Write-Host ('=' * 92) -ForegroundColor Cyan
  Write-Host ("  [$n] $title") -ForegroundColor Cyan
  Write-Host ('=' * 92) -ForegroundColor Cyan
  if ($msg) { Write-Host "  설명: $msg" -ForegroundColor Yellow }
}
function Run($lab, $pyargs) {
  Write-Host "  > py -3 $pyargs" -ForegroundColor DarkGray
  Push-Location (Join-Path $depth $lab)
  & py -3 $pyargs.Split(' ')
  Pop-Location
}

# --- 사전 점검 ---
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  Write-Host "[중단] Python 런처(py) 미설치. https://www.python.org 에서 설치하세요." -ForegroundColor Red
  return
}
Write-Host @"

  ##############################################################################
  #   Agentic AI 프롬프트 인젝션 — 통합 측정 프로젝트 라이브 데모
  #   breadth(단일 에이전트 벤치마크) + depth(전파/메모리/멀티모달/실프레임워크)
  #   핵심 메시지: 취약성은 '가정'이 아니라 '측정'해야 한다 (모델 의존)
  #   * 모든 도구는 mock — 실제 전송/삭제 없음, 더미 시크릿만 사용
  ##############################################################################
"@ -ForegroundColor Green
Pause-Step

# --- ① 멀티에이전트 체인 전파 (mock, 즉시) ---
Header '1/6' '멀티에이전트 체인 전파 (mock)' '오염문서 1개가 오케스트레이터→서브에이전트 체인을 따라 전파. 방어로 봉쇄.'
Run 'agent_injection_lab' "run.py --agents 6 --trials $MockTrials --show-chain"
Write-Host "  ☞ none 은 R0→…→끝까지 INF*(감염), 방어를 켜면 R0[INF*]→A1[ok] 로 전파가 봉쇄됩니다." -ForegroundColor Magenta
Pause-Step

# --- ② ingest x relay 2D 그리드 ---
Header '2/6' 'ingest x relay 2D 방어 매트릭스 (mock)' 'relay(가로)는 ASR 불변, ingest(세로)로 ASR 94→36→0%.'
Run 'agent_injection_lab' "run.py --grid --agents 6 --trials $MockTrials"
Write-Host "  ☞ relay 는 '폭발 반경', ingest 가 '침해(첫 hop 유출) 자체'를 막습니다." -ForegroundColor Magenta
Pause-Step

# --- ③ 메모리 cross-session 오염 ---
Header '3/6' '메모리/컨텍스트 오염 — cross-session (mock)' '세션 A가 장기 메모리에 심고 → 맥락 끊긴 세션 B가 검색만으로 발동.'
Run 'memory_poisoning_lab' "run.py --demo"
Write-Host "  ☞ 단 한 번의 오염이 '다음 세션'에서 반복 발동. write_gate/read_sanitize 로 차단." -ForegroundColor Magenta
Pause-Step

# --- ④ 멀티모달 채널 ---
Header '4/6' '멀티모달 인젝션 채널 (mock)' '이미지 → OCR/EXIF/alt-text 추출 텍스트에 숨은 명령. cross-channel 일관성 방어.'
Run 'multimodal_injection_lab' "run.py --demo"
Pause-Step

# --- ⑤ nanoclaw 방어 게이트: 자기평가 vs 정직한 일반화 ---
Header '5/6' '실프레임워크 방어 게이트 — 정직성 시연' '자작 5종엔 4/4(캘리브레이션) vs held-out 적응형엔 회피율 높음.'
Run 'nanoclaw_attack_lab' "run_demo.py"
Write-Host "  ☞ 위 4/4 는 '자기평가'. 아래 적응형(held-out)이 '정직한 일반화 수치'입니다." -ForegroundColor Magenta
Pause-Step
Run 'nanoclaw_attack_lab' "run_demo.py --adaptive"
Pause-Step

# --- ⑥ 하이라이트: 실모델 3B vs 8B ---
if ($Quick) {
  Header '6/6' '실모델 3B vs 8B (생략됨 - Quick 모드)' '저장된 결과로 대신 보여주세요: depth_labs/agent_injection_lab/results/result_ollama_llama3.{1,2}.json'
} else {
  $ollamaOk = $false
  if (Get-Command ollama -ErrorAction SilentlyContinue) {
    $ml = (& ollama list) 2>$null | Out-String
    if ($ml -match 'llama3\.2' -and $ml -match 'llama3\.1') { $ollamaOk = $true }
  }
  Header '6/6' '★ 하이라이트 — 실모델 3B vs 8B (같은 공격, 다른 결과)' '작은 모델은 굴복(ASR 100%), 큰 모델은 노출돼도 거부(ASR 0%). 취약성은 모델 의존 → 측정이 필요.'
  if ($ollamaOk) {
    Write-Host "`n  [3B] llama3.2 — 인젝션에 굴복하는지" -ForegroundColor Yellow
    Run 'agent_injection_lab' "run.py --backend ollama --model llama3.2 --agents 4 --trials $Trials"
    Write-Host "`n  [8B] llama3.1 — 노출돼도 거부하는지" -ForegroundColor Yellow
    Run 'agent_injection_lab' "run.py --backend ollama --model llama3.1 --agents 4 --trials $Trials"
    Write-Host "  ☞ ASR 100%(3B) vs 0%(8B). mock 의 단일 가정(0.95)은 작은 모델엔 과소·큰 모델엔 과대." -ForegroundColor Magenta
  } else {
    Write-Host "  [건너뜀] Ollama 또는 모델(llama3.2/llama3.1) 미설치 — 저장된 결과로 대신:" -ForegroundColor Red
    Write-Host "    depth_labs/agent_injection_lab/results/result_ollama_llama3.2.json  (3B → ASR 100%)" -ForegroundColor Gray
    Write-Host "    depth_labs/agent_injection_lab/results/result_ollama_llama3.1.json  (8B → ASR 0%)" -ForegroundColor Gray
    Write-Host "    설치: https://ollama.com  후  ollama pull llama3.2 ; ollama pull llama3.1" -ForegroundColor Gray
  }
}

Write-Host ''
Write-Host ('=' * 92) -ForegroundColor Green
Write-Host "  데모 끝. 상세 Q&A/한계/증거는  PROFESSOR_REVIEW_PREP.md  를 보세요." -ForegroundColor Green
Write-Host ('=' * 92) -ForegroundColor Green
