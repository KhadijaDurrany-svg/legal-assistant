"""Deterministic clause-type classification via weighted cue scoring.

Each clause is scored against every :class:`ClauseType` by summing the weights
of the cues (from :mod:`clausewise.cues`) that match its heading and body. The
heading is weighted more heavily than the body because a clause heading is a
strong signal of intent. The argmax type wins if it clears ``TYPE_THRESHOLD``;
otherwise the clause is ``OTHER``.
"""

from __future__ import annotations

from .cues import CUES, TYPE_THRESHOLD
from .models import ClauseType

_HEADING_BONUS = 1.5  # cue hits in the heading count extra


def score_clause(heading: str, body: str) -> dict[ClauseType, float]:
    """Return the per-type score for one clause."""
    scores: dict[ClauseType, float] = {}
    for ctype, cues in CUES.items():
        total = 0.0
        for pattern, weight in cues:
            if pattern.search(body):
                total += weight
            if heading and pattern.search(heading):
                total += weight * _HEADING_BONUS
        if total:
            scores[ctype] = total
    return scores


def classify_clause(heading: str, body: str) -> tuple[ClauseType, float]:
    """Classify one clause, returning ``(type, winning_score)``."""
    scores = score_clause(heading, body)
    if not scores:
        return ClauseType.OTHER, 0.0
    best_type = max(scores, key=lambda t: (scores[t], -_TIEBREAK.index(t)))
    best_score = scores[best_type]
    if best_score < TYPE_THRESHOLD:
        return ClauseType.OTHER, best_score
    return best_type, best_score


# Deterministic tie-break ordering so equal scores never depend on dict order.
_TIEBREAK: list[ClauseType] = list(ClauseType)
