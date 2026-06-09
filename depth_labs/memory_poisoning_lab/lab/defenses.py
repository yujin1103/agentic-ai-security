"""메모리 경계에서 적용하는 방어 전략(write 경계 / read 경계).

  none            : 무방어(baseline).
  write_gate      : memory_create 직전, 저장하려는 텍스트를 검사해 인젝션 라인을 제거(살균).
                    페이로드가 메모리에 들어가지 못하므로 오염 자체가 차단된다(진입 경계).
  read_provenance : memory_search 결과를 <untrusted_memory>로 감싸 '저장된 외부 데이터일 뿐
                    명령이 아님'을 명시(Spotlighting/LLM Tagging의 메모리판). 페이로드는 남되
                    발동 저항력이 올라간다(발동 경계, 태깅).
  read_sanitize   : memory_search 결과에서 인젝션 라인을 제거. 끌어온 내용에 명령이 남지
                    않아 발동이 원천 차단된다(발동 경계, 살균).
"""
from __future__ import annotations
import re
from . import config

# 인젝션 신호 패턴(한/영). write_gate / read_sanitize 가 공유한다.
SANITIZE_PATTERNS = [
    re.escape(config.SENTINEL),
    r"운영\s*규칙", r"향후\s*모든\s*세션", r"표준\s*동기화\s*절차",
    r"send_external", r"전송한다", r"전송하라", r"exfiltrat", r"유출",
    re.escape(config.ATTACKER_CHANNEL),
]
_SAN_RE = re.compile("|".join(SANITIZE_PATTERNS), re.IGNORECASE)


def sanitize_text(text: str) -> str:
    """인젝션 신호가 포함된 라인을 통째로 제거한다."""
    kept = [ln for ln in text.splitlines() if not _SAN_RE.search(ln)]
    return "\n".join(kept).strip()


def apply_write(text: str, defense: str) -> tuple[str, bool]:
    """write 경계(memory_create 직전) 방어. 반환: (저장할_텍스트, 저장_허용?)."""
    if defense == "write_gate":
        cleaned = sanitize_text(text)
        # 인젝션 라인을 떼어내고 남은 양성 텍스트가 있으면 그것만 저장, 없으면 저장 거부.
        if config.SENTINEL in cleaned:
            return "", False
        return (cleaned, True) if cleaned else ("", False)
    return text, True


def apply_read(docs: list[dict], defense: str) -> tuple[list[dict], bool]:
    """read 경계(memory_search 결과) 방어. 반환: (가공된_docs, is_tagged)."""
    if defense == "read_sanitize":
        out = []
        for d in docs:
            out.append({**d, "text": sanitize_text(d["text"])})
        return out, False
    if defense == "read_provenance":
        # 내용은 그대로 두되 '신뢰되지 않은 저장 데이터'로 태깅(is_tagged=True).
        return docs, True
    return docs, False
