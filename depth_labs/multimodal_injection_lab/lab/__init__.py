"""Multimodal (Image-Derived Text Channel) Indirect Injection Lab.

에이전트가 '이미지'(문서/스크린샷)를 OCR/EXIF/alt-text 추출 도구로 처리할 때, 그 추출 텍스트
채널에 숨은 지시가 명령으로 오인되어 더미 비밀이 유출되는 간접 인젝션을 재현/계측하는 하니스.
모달리티 '표면'을 모델링하며(채널), 실 VLM 의 in-image 취약성 측정은 범위 밖이다(README §한계).
"""
from . import config, assets, defenses, tools, llm, agent, metrics, runner

__all__ = ["config", "assets", "defenses", "tools", "llm", "agent", "metrics", "runner"]
