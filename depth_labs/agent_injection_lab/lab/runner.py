"""실험 스윕 실행기: 방어별로 여러 trial 을 돌려 지표를 집계한다.

[교수 점검 반영]
- 공통난수(CRN): trial_seed = seed*1_000_000 + t (방어 인덱스 d_idx 를 시드에서 제거).
  같은 t 는 모든 방어에서 동일한 trial_seed → 에이전트별 RNG((trial_seed,agent_id))도 동일.
  덕분에 방어 비교가 paired 가 되고, 과거 d_idx*1000 로 인한 (a) 방어 간 시드 노이즈와
  (b) trials>=1000 에서의 시드 충돌이 모두 사라진다.
- 클라이언트는 루프 밖에서 1회 생성(객체 churn 제거).
- run_grid(): ingest × relay 2D 스윕 — relay 단독으로는 ASR 이 안 떨어지지만 ingest 방어를
  켜면 ASR(첫 hop 유출)이 실제로 떨어짐을 보이기 위한 핵심 보강.
"""
from __future__ import annotations
from . import config, metrics
from .llm import make_client
from .orchestrator import ChainOrchestrator, build_roles
from .tools import ToolRegistry

_SLOT = 1_000_000   # trial 슬롯 폭(아주 큼) — 충돌 방지


def _trial_seed(seed: int, t: int) -> int:
    return seed * _SLOT + t


def run_sweep(backend: str = "mock", model: str = "llama3.1", n_agents: int = 5,
              trials: int = 20, ingest_defense: str = "none",
              relay_defenses: list[str] | None = None, seed: int = 42,
              temperature: float = 0.0, poison_index: int = 0,
              keep_sample: bool = True, egress_guard: bool = False) -> dict:
    """relay 방어 전략별 스윕(ingest_defense 고정). egress_guard: 출력 경계 방어 on/off."""
    relay_defenses = relay_defenses or list(config.DEFENSES)
    roles = build_roles(n_agents)
    llm = make_client(backend, model=model, temperature=temperature)
    by_defense: dict[str, dict] = {}
    samples: dict[str, str] = {}

    for relay in relay_defenses:
        trial_results = []
        for t in range(trials):
            tools = ToolRegistry(trial_id=f"{relay}.{t}")   # 기본 비기록(메모리만)
            orch = ChainOrchestrator(roles, llm, tools, config.SANDBOX_SECRET,
                                     ingest_defense=ingest_defense, relay_defense=relay,
                                     egress_guard=egress_guard)
            tr = orch.run_once(_trial_seed(seed, t), poison_index=poison_index)
            trial_results.append(tr)
            # 대표 샘플: 첫 '감염 발생' trial(없으면 첫 trial). 우연한 미감염 샘플 회피.
            if keep_sample and (relay not in samples or
                                (any(x.infected for x in tr.traces) and "INF*" not in samples[relay])):
                samples[relay] = metrics.render_chain(tr)
        by_defense[relay] = metrics.aggregate(trial_results)

    metrics.add_containment(by_defense)
    for relay in by_defense:
        by_defense[relay]["sample_chain"] = samples.get(relay, "")

    return {
        "config": {
            "backend": backend, "model": model if backend in ("ollama", "gemini") else None,
            "n_agents": n_agents, "trials": trials, "ingest_defense": ingest_defense,
            "relay_defenses": relay_defenses, "seed": seed, "temperature": temperature,
            "egress_guard": egress_guard,
            "mock_susceptibility": config.MOCK_SUSCEPTIBILITY if backend == "mock" else None,
            "roles": [r for r, _ in roles],
        },
        "by_defense": by_defense,
    }


def run_grid(backend: str = "mock", model: str = "llama3.1", n_agents: int = 5,
             trials: int = 200, ingest_defenses: list[str] | None = None,
             relay_defenses: list[str] | None = None, seed: int = 42,
             temperature: float = 0.0, poison_index: int = 0) -> dict:
    """ingest × relay 2D 스윕. 각 셀의 ASR / IR / 봉쇄 핵심값을 집계한다."""
    ingest_defenses = ingest_defenses or ["none", "tagging", "sanitize"]
    relay_defenses = relay_defenses or list(config.DEFENSES)
    roles = build_roles(n_agents)
    llm = make_client(backend, model=model, temperature=temperature)
    grid: dict[str, dict[str, dict]] = {}

    for ingest in ingest_defenses:
        grid[ingest] = {}
        for relay in relay_defenses:
            trs = []
            for t in range(trials):
                tools = ToolRegistry(trial_id=f"{ingest}.{relay}.{t}")
                orch = ChainOrchestrator(roles, llm, tools, config.SANDBOX_SECRET,
                                         ingest_defense=ingest, relay_defense=relay)
                trs.append(orch.run_once(_trial_seed(seed, t), poison_index=poison_index))
            agg = metrics.aggregate(trs)
            grid[ingest][relay] = {
                "asr": agg["attack_success_rate"], "asr_ci95": agg["asr_ci95"],
                "ir": agg["mean_infection_rate"], "mean_n_infected": agg["mean_n_infected"],
                "relay_fidelity": agg["mean_relay_fidelity"],
            }
    return {
        "config": {"backend": backend, "model": model if backend == "ollama" else None,
                   "n_agents": n_agents, "trials": trials, "seed": seed,
                   "ingest_defenses": ingest_defenses, "relay_defenses": relay_defenses,
                   "mock_susceptibility": config.MOCK_SUSCEPTIBILITY if backend == "mock" else None},
        "grid": grid,
    }


def parse_chain_specs(specs_str: str) -> list[tuple[str, str]]:
    """'ollama:llama3.2,gemini:gemini-2.5-flash,mock:' → [(backend, model), ...]."""
    out = []
    for tok in specs_str.split(","):
        tok = tok.strip()
        if not tok:
            continue
        be, _, mo = tok.partition(":")
        out.append((be.strip(), mo.strip()))
    return out


def run_cross_model(specs: list[tuple[str, str]], n_agents: int = 5, trials: int = 8,
                    seed: int = 42, temperature: float = 0.0, poison_index: int = 0,
                    ingest_defense: str = "none", relay_defense: str = "none",
                    egress_guard: bool = False) -> dict:
    """이종(모델 간) 체인. 에이전트 i 는 specs[i % len] 모델을 쓴다.

    한 키(공급자)면 키 하나로 충분: 같은 spec 은 클라이언트를 공유한다. 위치별 감염률과
    'agent-0 과 다른 모델 위치가 감염됐는가(모델 간 전파)'를 측정한다.
    """
    roles = build_roles(n_agents)
    cache: dict[tuple[str, str], object] = {}
    per_agent, labels = [], []
    for i in range(n_agents):
        be, mo = specs[i % len(specs)]
        if (be, mo) not in cache:
            cache[(be, mo)] = make_client(be, model=mo or "llama3.1", temperature=temperature)
        per_agent.append(cache[(be, mo)])
        labels.append(f"{be}:{mo or 'default'}")

    trial_results = []
    for t in range(trials):
        tools = ToolRegistry(trial_id=f"xmodel.{t}")
        orch = ChainOrchestrator(roles, per_agent[0], tools, config.SANDBOX_SECRET,
                                 ingest_defense=ingest_defense, relay_defense=relay_defense,
                                 egress_guard=egress_guard, llms=per_agent)
        trial_results.append(orch.run_once(_trial_seed(seed, t), poison_index=poison_index))

    n = len(trial_results)
    per_pos = []
    for i in range(n_agents):
        infected = sum(1 for tr in trial_results if tr.traces[i].infected)
        forwarded = sum(1 for tr in trial_results if tr.traces[i].forwarded_payload)
        exposed = sum(1 for tr in trial_results if tr.traces[i].exposed)
        per_pos.append({"pos": i, "model": labels[i],
                        "exposure_rate": exposed / n if n else 0.0,
                        "infection_rate": infected / n if n else 0.0,
                        "forward_rate": forwarded / n if n else 0.0})
    agg = metrics.aggregate(trial_results)
    # 모델 간 전파: agent-0 과 '다른 모델'인 하류 위치가 1번이라도 감염됐는가.
    cross = any(per_pos[i]["infection_rate"] > 0 and labels[i] != labels[0]
                for i in range(1, n_agents))
    return {
        "config": {"chain": labels, "trials": trials, "n_agents": n_agents, "seed": seed,
                   "ingest_defense": ingest_defense, "relay_defense": relay_defense,
                   "egress_guard": egress_guard},
        "per_position": per_pos,
        "overall": {"asr": agg["attack_success_rate"], "ir": agg["mean_infection_rate"],
                    "depth_given_breach": agg["mean_depth_given_breach"]},
        "cross_model_propagation": cross,
        "sample_chain": metrics.render_chain(trial_results[0]) if trial_results else "",
    }
