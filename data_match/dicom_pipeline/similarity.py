from __future__ import annotations

from difflib import SequenceMatcher


def _ratio_fallback(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def similarity_ratio(a: str | None, b: str | None) -> float:
    """Return similarity ratio in [0, 1]. Uses rapidfuzz if available."""

    a = (a or "").strip()
    b = (b or "").strip()

    try:
        from rapidfuzz.fuzz import ratio as rf_ratio

        return rf_ratio(a, b) / 100.0
    except Exception:
        return _ratio_fallback(a, b)
