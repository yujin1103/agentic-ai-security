"""데모 오케스트레이터.

[offline 모드] (모델/컨테이너 불필요 — 지금 바로 실행 가능)
  방어 게이트(review_gate)를 페이로드 세트에 적용해 탐지율/오탐율을 측정한다.
  '방어 ON일 때 어떤 인젝션이 에이전트에 도달조차 못 하는가'를 정량화한다.

[live 모드] (NanoClaw 구동 후 — README 런북 참고)
  실제 세션 inbound.db에 주입하고 관측 리스너로 exfil 발생 여부를 측정한다.
  방어 OFF(공격 성공률) vs 방어 ON(차단) before/after 비교.

[adaptive 모드] (HELD-OUT 일반화 평가 — 정직성 보정)
  review_gate.SIGNALS 는 payloads.py 에서 베껴왔기에 그 세트의 4/4 차단은
  train==test(자기 보정값)다. --adaptive 는 게이트 개발에 안 쓰인 별도
  adaptive_payloads 세트에 게이트를 적용해 '몇 개나 빠져나가는지(EVADE)'를
  정직하게 보고한다. 기대값: 대부분 회피(=일반화 한계 노출).

사용:
  python run_demo.py                       # offline: 5종 자기-보정(self-test) 표
  python run_demo.py --adaptive            # held-out 적응형 공격 탐지율(일반화)
  python run_demo.py --live --db <inbound.db>   # live 주입(README 절차 선행 필요)
"""
from __future__ import annotations
import argparse
import adaptive_payloads
import payloads
import review_gate


def offline():
    print("=" * 84)
    print(" 데모 A — 자동 검토 게이트(방어) 오프라인 평가  [SELF-TEST / 보정]")
    print(" 질문: 방어 ON이면 각 인젝션이 에이전트에 '도달조차' 못 하게 막히는가?")
    print(" 주의: 아래 5종은 게이트 신호를 만든 바로 그 자가-저작 세트다(train==test).")
    print("       따라서 4/4 차단은 '일반화'가 아니라 게이트 보정값일 뿐이다.")
    print("       일반화(=held-out) 수치는 `python run_demo.py --adaptive` 참고.")
    print("=" * 84)
    hdr = f"{'payload':<14}{'level':<11}{'gate action':<12}{'score':>6}  reasons"
    print(hdr)
    print("-" * 84)
    blocked = sanitized = allowed = 0
    fp = fn = 0
    for p in payloads.PAYLOADS:
        v = review_gate.review(p["text"])
        is_attack = p["level"] != "control"
        if v.action == "block":
            blocked += 1
        elif v.action == "sanitize":
            sanitized += 1
        else:
            allowed += 1
        # 오탐/미탐 집계
        neutralized = v.action in ("block", "sanitize")
        if is_attack and not neutralized:
            fn += 1   # 미탐(공격을 통과시킴)
        if (not is_attack) and neutralized:
            fp += 1   # 오탐(정상 메시지를 막음)
        print(f"{p['id']:<14}{p['level']:<11}{v.action:<12}{v.score:>6}  {','.join(v.reasons)}")
    print("-" * 84)
    n_attack = sum(1 for p in payloads.PAYLOADS if p["level"] != "control")
    n_control = len(payloads.PAYLOADS) - n_attack
    print(f" 공격 페이로드 {n_attack}개 중 차단/살균 {n_attack - fn}개 "
          f"(미탐 {fn}개) → 무력화율 {100*(n_attack-fn)/n_attack:.0f}%")
    print(f" 정상 페이로드 {n_control}개 중 오탐 {fp}개 "
          f"→ 오탐율 {100*fp/max(n_control,1):.0f}%")
    print("\n해석: 방어 OFF면 (취약 모델 기준) 위 공격들이 에이전트를 구동해 시크릿을")
    print("      유출할 수 있다. 방어 ON이면 무력화된 항목은 inbound.db 기록 전에 차단된다.")
    print("      위 4/4 는 자가-저작 세트 기준 '보정값'이며 일반화가 아니다(=self-test).")
    print("      정직한 일반화 수치: `python run_demo.py --adaptive`.")
    print("      라이브 ASR(실제 유출 발생률)은 --live 모드 + 관측 리스너로 측정한다.")


def adaptive():
    print("=" * 84)
    print(" 데모 A' — HELD-OUT 적응형 공격 평가  [일반화 / 정직성 보정]")
    print(" 질문: 게이트 개발에 안 쓰인 '새로운' 회피 변형은 게이트를 얼마나 빠져나가는가?")
    print("=" * 84)
    hdr = f"{'payload':<26}{'technique':<26}{'gate action':<12}{'score':>5}  evade?"
    print(hdr)
    print("-" * 84)
    evaded = 0
    total = len(adaptive_payloads.ADAPTIVE_PAYLOADS)
    for p in adaptive_payloads.ADAPTIVE_PAYLOADS:
        v = review_gate.review(p["text"])
        # 'allow' = 게이트를 그대로 통과 = 회피 성공.
        is_evaded = (v.action == "allow")
        if is_evaded:
            evaded += 1
        mark = "EVADE ✅" if is_evaded else f"caught({v.action})"
        print(f"{p['id']:<26}{p['technique']:<26}{v.action:<12}{v.score:>5}  {mark}")
    print("-" * 84)
    detected = total - evaded
    det_rate = 100 * detected / total
    print(f" 적응형 공격 {total}개 중 게이트가 잡은 것 {detected}개 / 빠져나간 것 {evaded}개")
    print(f" ▶ adaptive-attacker 탐지율(generalization) = {det_rate:.0f}%  "
          f"(회피율 {100 - det_rate:.0f}%)")
    print()
    print(" 캡션: offline 의 4/4(=100%)는 게이트 '자가-저작' 세트에 대한 self-test")
    print("       보정값이지 일반화가 아니다. 위 held-out 적응형 세트에서는 키워드")
    print("       기반 1차 게이트가 다수 회피된다 — 이것이 '정직한 일반화 수치'다.")
    print("       (제로폭 변형은 NFKC+제로폭제거 정규화로 다시 잡히도록 견고화했고,")
    print("        남는 의미적 회피는 review(use_llm=True) 2차 LLM 심판이 필요하다.)")


def live(db: str):
    print("[live] 이 모드는 NanoClaw가 구동 중이고 세션 inbound.db 경로가 있어야 합니다.")
    print("       README의 '라이브 런북'을 따라 observe_server.py 를 먼저 띄우고,")
    print("       inject.py 로 방어 OFF/ON 주입을 각각 수행해 리스너의 EXFIL 건수를 비교하세요.")
    print(f"       대상 inbound.db: {db}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--adaptive", action="store_true",
                    help="held-out 적응형 공격에 대한 일반화 탐지율 측정")
    ap.add_argument("--db", default="")
    args = ap.parse_args()
    if args.live:
        live(args.db)
    elif args.adaptive:
        adaptive()
    else:
        offline()


if __name__ == "__main__":
    main()
