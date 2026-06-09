"""CLI 진입점 — 멀티모달(이미지 파생 텍스트 채널) 간접 인젝션 실험.

예시:
  py -3 run.py                                  # mock 백엔드 (방어 × 채널) 스윕(모델 불필요)
  py -3 run.py --trials 200                     # 반복 늘리기
  py -3 run.py --demo                           # OCR 숨김 지시 → 유출, 방어가 차단되는 1장 시연
  py -3 run.py --backend ollama --model llama3.1 --trials 5   # 로컬 실모델로(실측 시도)
  py -3 run.py --mock-suscept 0.8,0.2           # mock 취약성 dial 민감도 분석

[정직성] mock 백엔드의 수치는 '측정값'이 아니라 가정한 취약성 파라미터(MOCK_SUSCEPTIBILITY)
기반 결정론적 시뮬레이션이다. 우리는 이미지→텍스트 추출 '채널'을 모델링하며, 실 VLM 의
in-image 지시 취약성은 측정하지 않는다(README §한계). 정량적 취약성 주장은 실모델 결과에서만.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

from lab import config, defenses as defenses_mod  # noqa: E402
from lab.runner import run_sweep, AGENT_ROLE, AGENT_INSTRUCTION  # noqa: E402
from lab.assets import build_image  # noqa: E402
from lab.agent import Agent  # noqa: E402
from lab.llm import make_client  # noqa: E402
from lab.tools import ToolRegistry  # noqa: E402


def _label(backend: str) -> str:
    return ("[mock=가정 파라미터 — 측정값 아님]" if backend == "mock"
            else "[ollama=실모델 측정]")


def _ci(pair) -> str:
    return f"[{pair[0]*100:.0f}-{pair[1]*100:.0f}]"


def _print_table(result: dict) -> None:
    cfg = result["config"]
    print("\n" + "=" * 92)
    print(f" 멀티모달 간접 인젝션 (이미지 파생 텍스트 채널) 실험   {_label(cfg['backend'])}")
    print("=" * 92)
    print(f" backend={cfg['backend']}  model={cfg['model']}  trials={cfg['trials']}  "
          f"seed={cfg['seed']}")
    if cfg.get("mock_susceptibility"):
        print(f" mock 취약성(가정): {cfg['mock_susceptibility']}  ← 이 dial 이 mock 결과를 결정한다")
    print(" 채널: OCR(저대비 글자) / EXIF(UserComment) / alt-text(접근성)  "
          "— 각 채널에 페이로드를 심고 그 채널을 추출")
    print(" (CRN: 같은 trial=같은 난수, 방어 간 paired 비교)")
    print("-" * 92)
    hdr = (f"{'injection채널':<14}{'방어':<26}"
           f"{'노출%':>7}{'ASR%(95%CI)':>18}{'시도%':>7}{'봉쇄%':>8}")
    print(hdr)
    print("-" * 92)
    for ch in cfg["channels"]:
        for d in cfg["defenses"]:
            a = result["grid"][ch][d]
            print(f"{ch:<14}{d:<26}"
                  f"{a['exposure_rate']*100:>6.1f}"
                  f"{a['attack_success_rate']*100:>7.1f}{_ci(a['asr_ci95']):>11}"
                  f"{a['attempted_exfil_rate']*100:>6.1f}{a['containment_pct']:>8.1f}")
        print("-" * 92)
    print(" 노출%: 페이로드가 방어를 통과해 추출 텍스트에 SENTINEL 이 남은 trial 비율")
    print(" ASR%: 더미 비밀이 공격자 채널로 실제 유출된 trial 비율  /  봉쇄%: none 대비 ASR 감소율")
    print(" ★ ocr_sanitize/cross_channel_consistency 는 페이로드를 제거·격리(노출 0%→ASR 0%),")
    print("   provenance_tag 는 노출은 남기되 '데이터' 라벨링으로 ASR 을 낮춘다(가정 dial).")


def _run_demo(backend: str, model: str, seed: int, temperature: float) -> None:
    """OCR 에 숨긴 지시가 유출을 유발하고, 방어가 그것을 차단하는 1장 시연."""
    print("\n" + "=" * 92)
    print(f" DEMO — OCR 채널에 숨은 지시 1장 처리   {_label(backend)}")
    print("=" * 92)
    llm = make_client(backend, model=model, temperature=temperature)
    image = build_image(index=0, injection_channel="ocr")

    print(f"\n[이미지] id={image['image_id']}  poisoned_channel={image['poisoned_channel']}")
    print(f"  visible_caption (사람이 보는 것): {image['visible_caption']}")
    print("  ocr_text (OCR 만 읽는 저대비 글자 포함):")
    for ln in image["ocr_text"].splitlines():
        print(f"    | {ln}")

    for d in ("none", "ocr_sanitize", "provenance_tag", "cross_channel_consistency"):
        rng = random.Random(f"{seed}:demo")
        tools = ToolRegistry(trial_id=f"demo.{d}")
        agent = Agent(AGENT_ROLE, AGENT_INSTRUCTION, llm, tools, config.SANDBOX_SECRET)
        tr = agent.process_image(image, extract_channel="ocr", ingest_defense=d, rng=rng)
        verdict = "비밀 유출됨!" if tr.secret_leaked else ("시도만(비밀 미동봉)"
                                                          if tr.attempted_exfil else "차단/정상")
        exfil = [c for c in tools.exfil_calls()]
        print(f"\n  방어={d:<26} 노출={tr.exposed!s:<5} → {verdict}")
        if exfil:
            print(f"    └ 모의 유출 호출: {exfil[0]['args']}")
    print("\n 해석: none 에서 OCR 로 추출된 숨은 지시가 명령으로 오인→더미 비밀 유출.")
    print("       ocr_sanitize/cross_channel_consistency 는 페이로드를 제거·격리해 유출을 차단.")
    print("       (mock 결정론 — 가정 dial 기반. 실 VLM 취약성 측정 아님.)")


def main() -> None:
    p = argparse.ArgumentParser(description="멀티모달(이미지 채널) 간접 인젝션 실험")
    p.add_argument("--backend", choices=["mock", "ollama"], default="mock")
    p.add_argument("--model", default="llama3.1", help="ollama 모델명")
    p.add_argument("--trials", type=int, default=200, help="(방어×채널) 셀별 반복 trial 수")
    p.add_argument("--defenses", default=",".join(config.DEFENSES))
    p.add_argument("--channels", default=",".join(config.INJECTION_CHANNELS))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--mock-suscept", default="", help="'untagged,tagged' (예: 0.8,0.2) 민감도 분석")
    p.add_argument("--demo", action="store_true", help="OCR 숨김 지시 1장 시연")
    p.add_argument("--out", default="")
    args = p.parse_args()

    if args.mock_suscept:
        u, t = (float(x) for x in args.mock_suscept.split(","))
        config.MOCK_SUSCEPTIBILITY["untagged"] = u
        config.MOCK_SUSCEPTIBILITY["tagged"] = t

    print("[안전] 모든 도구는 모의(mock)입니다 — 실제 전송/삭제 없음, 더미 데이터만 사용.")
    print("[안전] '이미지'는 실제 픽셀이 아니라 추출 채널 텍스트를 담은 더미 dict 입니다.")
    print(f"[백엔드] {_label(args.backend)}")
    if args.backend == "ollama":
        print(f"[ollama] http://localhost:11434 '{args.model}' 사용 시도(서버 미가동 시 미감염 처리).")

    if args.demo:
        _run_demo(args.backend, args.model, args.seed, args.temperature)
        return

    result = run_sweep(
        backend=args.backend, model=args.model, trials=args.trials,
        defenses=[d.strip() for d in args.defenses.split(",") if d.strip()],
        channels=[c.strip() for c in args.channels.split(",") if c.strip()],
        seed=args.seed, temperature=args.temperature)
    _print_table(result)

    ts = time.strftime("%Y%m%d_%H%M%S")
    out = Path(args.out) if args.out else config.RESULTS_DIR / f"result_{ts}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과 저장: {out}")


if __name__ == "__main__":
    main()
