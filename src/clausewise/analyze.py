"""Top-level analysis pipeline: text -> :class:`Report`.

``analyze`` is the single entry point used by the CLI, the benchmark and the
tests. It is pure and deterministic: the same text always yields the same
report, with no I/O.
"""

from __future__ import annotations

from .classify import classify_clause
from .models import Clause, Report
from .risk import flag_risks
from .segment import split_clauses


def analyze(text: str) -> Report:
    """Segment, classify and risk-flag a contract given as plain text."""
    clauses: list[Clause] = []
    for i, (heading, body) in enumerate(split_clauses(text)):
        ctype, score = classify_clause(heading, body)
        clauses.append(
            Clause(index=i, heading=heading, text=body, clause_type=ctype, type_score=round(score, 3))
        )
    findings = flag_risks(clauses)
    return Report(clauses=clauses, findings=findings)
