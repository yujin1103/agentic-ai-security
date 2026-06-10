"""멀티에이전트 체인 오케스트레이터.

토폴로지: 오케스트레이터가 에이전트 0..N-1 을 순차 체인으로 호출한다.
  - 에이전트 0(researcher) 는 외부 문서(오염 문서 포함)를 입력으로 받는다.
  - 에이전트 i(i>0) 는 직전 에이전트의 출력 메시지를 입력으로 받는다.
방어 적용 지점은 두 곳:
  - ingest_defense : 외부 문서를 처음 받아들일 때(입력 경계)
  - relay_defense  : 에이전트 간 메시지를 넘길 때(전파 경계) ← 전파 봉쇄 실험의 핵심

[난수 설계 — 공통난수(CRN, common random numbers)]
각 (trial, agent_id) 마다 **독립적이고 방어와 무관하게 고정된** RNG 를 쓴다
(random.Random((trial_seed, agent_id))). 따라서 같은 trial 에서 에이전트 0 의 감염 주사위
눈금은 어떤 방어에서도 동일하다 → ASR(=에이전트 0 감염에 지배됨)이 방어 간 '시드 노이즈'로
흔들리지 않고, 방어 효과를 짝지어(paired) 비교할 수 있다.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from . import config, defenses, payloads
from .agent import Agent, AgentTrace
from .llm import LLMClient
from .tools import ToolRegistry


@dataclass
class TrialResult:
    relay_defense: str
    ingest_defense: str
    n_agents: int
    traces: list[AgentTrace] = field(default_factory=list)
    exfil_calls: list[dict] = field(default_factory=list)
    relay_fidelity: float = 1.0   # relay 단계에서 '정상 요약'이 보존된 비율(boundary 의 trade-off 노출)


def build_roles(n: int) -> list[tuple[str, str]]:
    base = config.DEFAULT_ROLES
    roles = []
    for i in range(n):
        role, instr = base[i % len(base)]
        if i >= len(base):
            role = f"{role}{i}"
        roles.append((role, instr))
    return roles


class ChainOrchestrator:
    def __init__(self, roles, llm: LLMClient, tools: ToolRegistry, secret: str,
                 ingest_defense: str = "none", relay_defense: str = "none",
                 egress_guard: bool = False):
        self.roles = roles
        self.llm = llm
        self.tools = tools
        self.secret = secret
        self.ingest_defense = ingest_defense
        self.relay_defense = relay_defense
        self.egress_guard = egress_guard   # 출력 경계(egress) 방어 — 모델 무관

    def run_once(self, trial_seed: int, poison_index: int = 0) -> TrialResult:
        # 외부 문서 수집(오염 문서 포함) → 에이전트 0 입력(입력 경계 방어 적용)
        external = "\n\n".join(payloads.build_documents(poison_index))
        msg, tagged = defenses.apply(external, self.ingest_defense)

        traces: list[AgentTrace] = []
        n_relays = relays_kept = 0
        for i, (role, instr) in enumerate(self.roles):
            # CRN: 방어와 무관하게 (trial, agent) 고정 RNG → 같은 trial 의 같은 hop 은 동일 주사위.
            # (random.Random 은 튜플 시드를 받지 않으므로 문자열 시드로 결합한다.)
            rng = random.Random(f"{trial_seed}:{i}")
            agent = Agent(i, role, instr, self.llm, self.tools, self.secret,
                          egress_guard=self.egress_guard)
            out_msg, trace = agent.act(msg, tagged, rng)
            traces.append(trace)
            # 다음 에이전트로 넘기기 전, 전파 경계 방어 적용
            if i < len(self.roles) - 1:
                relayed, tagged = defenses.apply(out_msg, self.relay_defense)
                # relay fidelity(백엔드 무관): relay 결과가 비어있지 않고 boundary 의 고정
                # 대체문자열이 아니면 '정상 콘텐츠 보존'으로 본다. boundary 만 콘텐츠를 통째로
                # 파괴하므로 fidelity=0, none/tagging/sanitize 는 보존(~1.0)으로 측정된다.
                n_relays += 1
                if relayed.strip() and defenses.BOUNDARY_MARKER not in relayed:
                    relays_kept += 1
                msg = relayed

        return TrialResult(
            relay_defense=self.relay_defense, ingest_defense=self.ingest_defense,
            n_agents=len(self.roles), traces=traces,
            exfil_calls=self.tools.exfil_calls(),
            relay_fidelity=(relays_kept / n_relays) if n_relays else 1.0,
        )
