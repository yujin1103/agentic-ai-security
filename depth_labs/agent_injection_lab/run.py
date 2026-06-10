"""CLI 진입점 — 멀티에이전트 인젝션 전파 실험 실행.

예시:
  python run.py                                  # mock 백엔드 relay 방어 스윕(모델 불필요)
  python run.py --agents 8 --trials 200          # 체인 길이/반복 늘리기
  python run.py --grid                           # ingest × relay 2D 스윕(ASR 이 ingest 로 떨어짐)
  python run.py --backend ollama --model llama3.1 --trials 5   # 로컬 실모델로(실측)
  python run.py --show-chain                     # 방어별 샘플 체인 시각화
  python run.py --mock-suscept 0.8,0.2           # mock 취약성 dial 민감도 분석

[정직성] mock 백엔드의 수치는 '측정값'이 아니라 가정한 취약성 파라미터(MOCK_SUSCEPTIBILITY)
기반 결정론적 시뮬레이션이다. 정량적 취약성 주장은 --backend ollama(실모델) 결과에서만 성립.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

from lab import config  # noqa: E402
from lab.runner import run_sweep, run_grid, run_cross_model, parse_chain_specs  # noqa: E402


def _print_cross(result: dict) -> None:
    cfg = result["config"]
    print("\n" + "=" * 96)
    print(" 모델 간 전파(이종 체인) 실험 — 위치별 감염률   [실모델]")
    print("=" * 96)
    print(f" 체인: {' → '.join(cfg['chain'])}")
    print(f" trials={cfg['trials']}  ingest={cfg['ingest_defense']}  relay={cfg['relay_defense']}"
          f"  egress_guard={cfg['egress_guard']}")
    print("-" * 96)
    print(f"{'위치':<5}{'모델':<28}{'노출%':>9}{'감염%':>9}{'전파(forward)%':>16}")
    print("-" * 96)
    for p in result["per_position"]:
        print(f"{p['pos']:<5}{p['model']:<28}{p['exposure_rate']*100:>8.0f}%"
              f"{p['infection_rate']*100:>8.0f}%{p['forward_rate']*100:>15.0f}%")
    print("-" * 96)
    o = result["overall"]
    depth = o["depth_given_breach"]
    print(f" 전체 ASR={o['asr']*100:.0f}%  IR={o['ir']*100:.0f}%  "
          f"깊이|감염={depth:.2f}" if depth is not None else
          f" 전체 ASR={o['asr']*100:.0f}%  IR={o['ir']*100:.0f}%  깊이|감염=—")
    print(f" 모델 간 전파(agent-0 과 다른 모델 위치 감염)?: {result['cross_model_propagation']}")
    print(f" 샘플 체인: {result['sample_chain']}")


def _label(backend: str) -> str:
    if backend == "mock":
        return "[mock=가정 파라미터 기반 시뮬레이션 — 측정값 아님]"
    if backend == "gemini":
        return "[gemini=상용 실모델 측정]"
    return "[ollama=로컬 실모델 측정]"


def _ci(pair) -> str:
    return f"[{pair[0]*100:.0f}–{pair[1]*100:.0f}]"


def _print_table(result: dict) -> None:
    cfg = result["config"]
    print("\n" + "=" * 96)
    print(f" 멀티에이전트 프롬프트 인젝션 전파 실험 결과   {_label(cfg['backend'])}")
    print("=" * 96)
    print(f" backend={cfg['backend']}  model={cfg['model']}  agents={cfg['n_agents']}  "
          f"trials={cfg['trials']}  ingest_defense={cfg['ingest_defense']}  seed={cfg['seed']}")
    if cfg.get("egress_guard"):
        print(" egress_guard=ON  → 출력 경계 차단(모델 무관). 모델이 감염돼도 비밀이 못 나가 ASR=0 기대.")
    if cfg.get("mock_susceptibility"):
        print(f" mock 취약성(가정): {cfg['mock_susceptibility']}  ← 이 dial 이 mock 결과를 결정한다")
    print(f" 체인: {' → '.join(cfg['roles'])}   (CRN: 방어 간 동일 trial=동일 난수, paired 비교)")
    print("-" * 96)
    hdr = (f"{'relay 방어':<11}{'IR%(95%CI)':>16}{'평균감염':>9}{'깊이|감염':>9}"
           f"{'ASR%(95%CI)':>16}{'봉쇄%':>7}{'fidelity':>9}")
    print(hdr)
    print("-" * 96)
    for d in cfg["relay_defenses"]:
        a = result["by_defense"][d]
        depth = a["mean_depth_given_breach"]
        depth_s = f"{depth:.2f}" if depth is not None else "—"
        print(f"{d:<11}{a['mean_infection_rate']*100:>6.1f}{_ci(a['infection_rate_ci95']):>10}"
              f"{a['mean_n_infected']:>9.2f}{depth_s:>9}"
              f"{a['attack_success_rate']*100:>6.1f}{_ci(a['asr_ci95']):>10}"
              f"{a['containment_pct']:>7.1f}{a['mean_relay_fidelity']*100:>8.0f}%")
    print("-" * 96)
    print(" 깊이|감염: 감염된 trial에 한해 도달한 최대 hop(미감염 trial 제외 → 음수/센티넬 없음)")
    print(" 봉쇄%: none 대비 평균 감염수 감소율(전파 축소이지 '유출 차단'이 아님 — ASR 참조)")
    print(" fidelity: relay 후 정상 요약 보존율. boundary 는 봉쇄 100%지만 fidelity 0%(채널 파괴 trade-off)")
    print(" ★ relay 방어만으로는 ASR(첫 hop 유출)이 거의 안 떨어진다 → `--grid` 로 ingest 방어 효과 확인")


def _print_grid(result: dict) -> None:
    cfg = result["config"]
    print("\n" + "=" * 96)
    print(f" ingest × relay 2D 방어 매트릭스 — ASR(%) [그리고 fidelity]   {_label(cfg['backend'])}")
    print("=" * 96)
    print(f" backend={cfg['backend']}  agents={cfg['n_agents']}  trials={cfg['trials']}  seed={cfg['seed']}")
    if cfg.get("mock_susceptibility"):
        print(f" mock 취약성(가정): {cfg['mock_susceptibility']}")
    relays = cfg["relay_defenses"]
    print("-" * 96)
    print(f"{'ingest \\ relay':<16}" + "".join(f"{r:>16}" for r in relays))
    print("-" * 96)
    for ingest in cfg["ingest_defenses"]:
        row = f"{ingest:<16}"
        for r in relays:
            cell = result["grid"][ingest][r]
            row += f"{cell['asr']*100:>9.0f}%/f{cell['relay_fidelity']*100:>3.0f}"
        print(row)
    print("-" * 96)
    print(" 각 셀 = ASR% / fidelity%.  핵심: relay 행 방향(→)으로는 ASR 이 거의 불변이지만,")
    print(" ingest 열 방향(↓)으로 ingest 방어를 켜면 ASR 이 급감한다 = '첫 hop 유출'은 ingest 가 막는다.")


def _print_chains(result: dict) -> None:
    print("\n[방어별 샘플 체인]  (INF*=감염/유출, exp=노출되었으나 미감염, ok=정상)")
    for d in result["config"]["relay_defenses"]:
        print(f"  {d:<10}: {result['by_defense'][d]['sample_chain']}")


def main() -> None:
    p = argparse.ArgumentParser(description="멀티에이전트 인젝션 전파 실험")
    p.add_argument("--backend", choices=["mock", "ollama", "gemini"], default="mock")
    p.add_argument("--model", default="llama3.1", help="ollama/gemini 모델명")
    p.add_argument("--agents", type=int, default=5, help="체인 내 에이전트 수")
    p.add_argument("--trials", type=int, default=20, help="방어별 반복 trial 수")
    p.add_argument("--ingest-defense", choices=config.DEFENSES, default="none")
    p.add_argument("--relay-defenses", default=",".join(config.DEFENSES))
    p.add_argument("--grid", action="store_true", help="ingest × relay 2D 스윕")
    p.add_argument("--ingest-defenses", default="none,tagging,sanitize", help="--grid 의 ingest 축")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--poison-index", type=int, default=0)
    p.add_argument("--mock-suscept", default="", help="'untagged,tagged' (예: 0.8,0.2) 민감도 분석")
    p.add_argument("--egress-guard", action="store_true",
                   help="출력 경계 방어 ON(모델 무관). 감염돼도 비밀 전송을 차단 → ASR 0 기대")
    p.add_argument("--chain-models", default="",
                   help="이종 체인(모델 간 전파): 'ollama:llama3.2,gemini:gemini-2.5-flash,ollama:llama3.2'")
    p.add_argument("--payload", choices=list(["blatant", "workflow", "tool_result", "audit_bot"]),
                   default="blatant", help="공격 페이로드 변형(정렬 모델엔 위장형이 필요)")
    p.add_argument("--secret-framing", choices=["guarded", "ambient"], default="guarded",
                   help="guarded=비밀을 '노출금지' 명시(방어↑) / ambient=평범한 환경 구성값(현실적)")
    p.add_argument("--show-chain", action="store_true")
    p.add_argument("--out", default="")
    args = p.parse_args()

    if args.mock_suscept:
        u, t = (float(x) for x in args.mock_suscept.split(","))
        config.MOCK_SUSCEPTIBILITY["untagged"] = u
        config.MOCK_SUSCEPTIBILITY["tagged"] = t
    config.INJECTION_VARIANT = args.payload   # 공격 페이로드 변형 선택
    config.SECRET_FRAMING = args.secret_framing   # 비밀 프레이밍(시나리오 현실성)

    print("[안전] 모든 도구는 모의(mock)입니다 — 실제 전송/삭제 없음, 더미 데이터만 사용.")
    print(f"[백엔드] {_label(args.backend)}")
    if args.backend == "ollama":
        print(f"[ollama] http://localhost:11434 '{args.model}' 사용 시도(서버 미가동 시 미감염 처리).")

    if args.chain_models:
        result = run_cross_model(
            parse_chain_specs(args.chain_models), n_agents=args.agents, trials=args.trials,
            seed=args.seed, temperature=args.temperature, poison_index=args.poison_index,
            ingest_defense=args.ingest_defense,
            relay_defense=args.relay_defenses.split(",")[0].strip() or "none",
            egress_guard=args.egress_guard)
        _print_cross(result)
        prefix = "xmodel"
    elif args.grid:
        result = run_grid(
            backend=args.backend, model=args.model, n_agents=args.agents, trials=args.trials,
            ingest_defenses=[d.strip() for d in args.ingest_defenses.split(",") if d.strip()],
            relay_defenses=[d.strip() for d in args.relay_defenses.split(",") if d.strip()],
            seed=args.seed, temperature=args.temperature, poison_index=args.poison_index)
        _print_grid(result)
        prefix = "grid"
    else:
        result = run_sweep(
            backend=args.backend, model=args.model, n_agents=args.agents, trials=args.trials,
            ingest_defense=args.ingest_defense,
            relay_defenses=[d.strip() for d in args.relay_defenses.split(",") if d.strip()],
            seed=args.seed, temperature=args.temperature, poison_index=args.poison_index,
            egress_guard=args.egress_guard)
        _print_table(result)
        if args.show_chain:
            _print_chains(result)
        prefix = "result"

    ts = time.strftime("%Y%m%d_%H%M%S")
    out = Path(args.out) if args.out else config.RESULTS_DIR / f"{prefix}_{ts}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과 저장: {out}")


if __name__ == "__main__":
    main()
