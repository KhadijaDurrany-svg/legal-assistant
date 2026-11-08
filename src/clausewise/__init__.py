"""clausewise — offline, deterministic contract clause extraction and risk flagging.

Segment a contract into clauses, classify each clause by type, and flag risky
clauses (auto-renewal, uncapped liability, one-sided termination, unlimited
indemnity) and missing protective clauses — with a reproducible benchmark of
detection quality against keyword and random baselines.

No network, no API keys, no model downloads.
"""

from __future__ import annotations

from .analyze import analyze
from .models import (
    Clause,
    ClauseType,
    Report,
    RiskCode,
    RiskFinding,
    Severity,
)

__version__ = "0.1.0"

__all__ = [
    "Clause",
    "ClauseType",
    "Report",
    "RiskCode",
    "RiskFinding",
    "Severity",
    "__version__",
    "analyze",
]
