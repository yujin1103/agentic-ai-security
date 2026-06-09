from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal

EffectType = Literal[
    "sent_email", "calendar_event", "drive_file", "slack_message", "transfer",
    "reservation", "memory", "file_deleted", "tool_sequence_min"
]

@dataclass(frozen=True)
class EffectSpec:
    type: EffectType
    where: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class UserTask:
    id: str
    suite: str
    prompt: str
    expected_effects: list[EffectSpec]
    recommended_min_tool_calls: int = 1
    notes: str = ""

@dataclass(frozen=True)
class InjectionTask:
    id: str
    goal: str
    expected_effect: EffectSpec
    dangerous_tool_hint: str
    notes: str = ""

@dataclass(frozen=True)
class AttackFamily:
    id: str
    name: str
    description: str
    template: str

@dataclass(frozen=True)
class SecurityCase:
    case_id: str
    user_task_id: str
    injection_task_id: str
    attack_family_id: str
    suite: str
    placeholder_id: str

@dataclass
class EvaluationResult:
    case_id: str
    user_task_id: str
    injection_task_id: str
    attack_family_id: str
    suite: str
    utility_ok: bool
    targeted_asr: bool
    utility_under_attack: bool
    tool_attempt_rate: int
    block_rate: int
    tool_call_count: int
    contamination_seen: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
