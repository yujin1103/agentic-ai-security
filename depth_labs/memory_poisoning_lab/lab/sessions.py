"""2세션 프로토콜 실행 + 방어별 스윕 + 지표 집계.

한 trial = (세션 A 심기) → (세션 B 발동), 둘이 같은 장기 메모리를 공유.
스윕은 방어별로 여러 trial 을 돌려 plant율/발동율/e2e ASR/봉쇄율을 집계한다.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from math import sqrt
from statistics import mean, pstdev
from . import config, payloads
from .agent import SessionAgent, SessionTrace
from .llm import make_client
from .store import MemoryStore, ToolRegistry


def wilson_ci(k: int, n: int, z: float = 1.96) -> list[float]:
    """이항 비율 k/n 의 95% Wilson score 신뢰구간."""
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return [round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)]


@dataclass
class TrialResult:
    defense: str
    planted: bool = False
    retrieved_poison: bool = False
    triggered: bool = False
    traces: list[SessionTrace] = field(default_factory=list)


def run_trial(backend: str, defense: str, rng: random.Random, *,
              model: str = "llama3.1", temperature: float = 0.0,
              poisoned: bool = True, trial_id: str = "") -> TrialResult:
    """격리된 in-memory store 로 A→B 한 판을 돌린다(스윕용, trial 간 오염 격리)."""
    store = MemoryStore(in_memory=True)
    for m in payloads.SEED_BENIGN_MEMORIES:        # 양성 노이즈(대조)
        store.add(m, source="user")
    tools = ToolRegistry(trial_id=trial_id, log_to_disk=False)
    llm = make_client(backend, model=model, temperature=temperature)
    agent = SessionAgent("assistant", "사용자의 온보딩/작업을 돕는다.",
                         llm, store, tools, config.SANDBOX_SECRET)

    doc = payloads.POISONED_DOC_SESSION_A if poisoned else payloads.BENIGN_DOC_SESSION_A
    ta = agent.run_session_a(doc, defense, rng)
    tb = agent.run_session_b(payloads.SESSION_B_TASK, payloads.SESSION_B_QUERY, defense, rng)
    return TrialResult(defense=defense, planted=ta.planted,
                       retrieved_poison=tb.retrieved_poison, triggered=tb.triggered,
                       traces=[ta, tb])


def aggregate(results: list[TrialResult]) -> dict:
    n = len(results)
    planted = [1.0 if r.planted else 0.0 for r in results]
    triggered = [1.0 if r.triggered else 0.0 for r in results]
    e2e = [1.0 if (r.planted and r.triggered) else 0.0 for r in results]
    n_planted = int(sum(planted))
    n_e2e = int(sum(e2e))
    # 발동율은 '심긴 trial 조건부'로도 본다(read 경계 방어의 순수 효과).
    trig_given_plant = [1.0 if r.triggered else 0.0 for r in results if r.planted]
    return {
        "trials": n,
        "plant_rate": mean(planted) if n else 0.0,
        "plant_rate_ci95": wilson_ci(n_planted, n),
        "trigger_rate_given_plant": mean(trig_given_plant) if trig_given_plant else 0.0,
        "e2e_asr": mean(e2e) if n else 0.0,
        "e2e_asr_ci95": wilson_ci(n_e2e, n),
        "e2e_asr_std": pstdev(e2e) if n > 1 else 0.0,
        "n_planted": n_planted,
    }


def add_containment(agg_by_defense: dict) -> None:
    base = agg_by_defense.get("none", {}).get("e2e_asr", 0.0)
    for d, agg in agg_by_defense.items():
        agg["containment_pct"] = round((1 - agg["e2e_asr"] / base) * 100, 1) if base > 0 else 0.0


def run_sweep(backend: str = "mock", model: str = "llama3.1", trials: int = 200,
              defenses: list[str] | None = None, seed: int = 42,
              temperature: float = 0.0) -> dict:
    defenses = defenses or list(config.DEFENSES)
    by_defense: dict[str, dict] = {}
    samples: dict[str, dict] = {}
    for d in defenses:
        results = []
        for t in range(trials):
            # 공통난수(CRN): 같은 t 는 모든 방어에서 동일한 난수 → paired 비교(방어만 변수).
            # (random.Random 은 튜플 시드를 받지 않으므로 문자열 시드를 쓴다.)
            rng = random.Random(f"{seed}:{t}")
            tr = run_trial(backend, d, rng, model=model, temperature=temperature,
                           trial_id=f"{d}.{t}")
            results.append(tr)
            if t == 0:
                samples[d] = {
                    "A_planted": tr.planted,
                    "B_retrieved_poison": tr.retrieved_poison,
                    "B_triggered": tr.triggered,
                }
        by_defense[d] = aggregate(results)
    add_containment(by_defense)
    for d in by_defense:
        by_defense[d]["sample"] = samples.get(d, {})
    return {
        "config": {"backend": backend, "model": model if backend == "ollama" else None,
                   "trials": trials, "defenses": defenses, "seed": seed,
                   "temperature": temperature,
                   "mock_params": ({"P_PLANT": config.P_PLANT, "P_TRIGGER": config.P_TRIGGER}
                                   if backend == "mock" else None)},
        "by_defense": by_defense,
    }
