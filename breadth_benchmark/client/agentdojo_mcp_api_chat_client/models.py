from __future__ import annotations

from typing import Iterable

API_MODELS = [
    "gpt-4.1-mini",   # default: broadly available and inexpensive
    "gpt-4.1",
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-5-mini",
    "gpt-5",
    "gpt-5.1",
    "gpt-5.2",
]


def resolve_model(index: int) -> str:
    if index < 0 or index >= len(API_MODELS):
        raise ValueError(f"Invalid model index {index}. Valid range: 0..{len(API_MODELS)-1}")
    return API_MODELS[index]


def preferred_available_model(available_ids: Iterable[str], requested: str) -> tuple[str, bool]:
    """Return requested if available, otherwise the first configured available model."""
    available = set(available_ids)
    if requested in available:
        return requested, False
    for candidate in API_MODELS:
        if candidate in available:
            return candidate, True
    return requested, False
