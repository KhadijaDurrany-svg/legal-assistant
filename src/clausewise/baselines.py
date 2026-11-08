"""Detectors under comparison in the benchmark.

A *detector* maps contract text to a set of :class:`RiskCode`. Three are
provided:

* :func:`detect_ours` — the full pipeline (segment -> classify -> risk rules);
* :func:`keyword_detector` — a single keyword per risk, no negation or scope
  handling (the naive baseline most ad-hoc scripts land on);
* :class:`RandomDetector` — seeded coin-flips, the floor.
"""

from __future__ import annotations

import re

import numpy as np

from .analyze import analyze
from .models import MISSING_RISKS, PRESENT_RISKS, RiskCode

ALL_RISKS: tuple[RiskCode, ...] = tuple(RiskCode)


def detect_ours(text: str) -> set[RiskCode]:
    """Our detector: the deterministic analysis pipeline's risk codes."""
    return analyze(text).risk_codes


# Keyword baseline: one substring per present-risk; its absence flags the
# matching missing-risk. No notion of clause type, cap, negation or party-side.
_KW_PRESENT: dict[RiskCode, re.Pattern[str]] = {
    RiskCode.AUTO_RENEWAL: re.compile(r"renew", re.IGNORECASE),
    RiskCode.UNCAPPED_LIABILITY: re.compile(r"liabilit", re.IGNORECASE),
    RiskCode.UNILATERAL_TERMINATION: re.compile(r"terminat", re.IGNORECASE),
    RiskCode.UNLIMITED_INDEMNITY: re.compile(r"indemnif", re.IGNORECASE),
}
_KW_MISSING: dict[RiskCode, re.Pattern[str]] = {
    RiskCode.MISSING_TERMINATION: re.compile(r"terminat", re.IGNORECASE),
    RiskCode.MISSING_LIABILITY_CAP: re.compile(r"liabilit", re.IGNORECASE),
    RiskCode.MISSING_GOVERNING_LAW: re.compile(r"governing law", re.IGNORECASE),
    RiskCode.MISSING_CONFIDENTIALITY: re.compile(r"confidential", re.IGNORECASE),
}


def keyword_detector(text: str) -> set[RiskCode]:
    found: set[RiskCode] = set()
    for code, pat in _KW_PRESENT.items():
        if pat.search(text):
            found.add(code)
    for code, pat in _KW_MISSING.items():
        if not pat.search(text):
            found.add(code)
    return found


class RandomDetector:
    """Flags each risk code independently with probability ``p`` (seeded)."""

    def __init__(self, seed: int, p: float = 0.5) -> None:
        self._rng = np.random.default_rng(seed)
        self._p = p

    def __call__(self, text: str) -> set[RiskCode]:
        return {code for code in ALL_RISKS if self._rng.random() < self._p}


__all__ = [
    "ALL_RISKS",
    "MISSING_RISKS",
    "PRESENT_RISKS",
    "RandomDetector",
    "detect_ours",
    "keyword_detector",
]
