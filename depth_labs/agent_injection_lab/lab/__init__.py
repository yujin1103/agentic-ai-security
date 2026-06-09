"""Multi-Agent Prompt Injection Propagation Lab.

멀티에이전트 체인에서 간접 프롬프트 인젝션의 자기전파를 실증/계측하고,
에이전트 간 방어(tagging/sanitize/boundary)의 전파 봉쇄 효과를 정량 비교하는 연구 하니스.
"""
from . import config, payloads, defenses, tools, llm, agent, orchestrator, metrics, runner

__all__ = ["config", "payloads", "defenses", "tools", "llm", "agent",
           "orchestrator", "metrics", "runner"]
