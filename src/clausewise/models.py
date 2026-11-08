"""Typed data models for clause analysis.

Everything the analyzer produces is a validated pydantic v2 model so that the
CLI, the benchmark harness and the tests share one contract. No model here
touches the network or the filesystem.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ClauseType(str, Enum):
    """Structural category a contract clause falls into.

    These are *document structure* labels, not risk labels. The risk layer
    (:mod:`clausewise.risk`) reasons on top of them.
    """

    TERM = "term"
    TERMINATION = "termination"
    LIABILITY = "liability"
    INDEMNIFICATION = "indemnification"
    CONFIDENTIALITY = "confidentiality"
    GOVERNING_LAW = "governing_law"
    PAYMENT = "payment"
    ASSIGNMENT = "assignment"
    FORCE_MAJEURE = "force_majeure"
    WARRANTY = "warranty"
    DISPUTE_RESOLUTION = "dispute_resolution"
    DEFINITIONS = "definitions"
    NOTICES = "notices"
    OTHER = "other"


class RiskCode(str, Enum):
    """A specific risk the flagger can raise about a contract.

    Split into *present* risks (a risky clause is in the document) and
    *missing* risks (a clause that ought to be there is absent).
    """

    # Present risks: a risky clause is in the document.
    AUTO_RENEWAL = "auto_renewal"
    UNCAPPED_LIABILITY = "uncapped_liability"
    UNILATERAL_TERMINATION = "unilateral_termination"
    UNLIMITED_INDEMNITY = "unlimited_indemnity"
    # Missing risks: an expected protective clause is absent.
    MISSING_TERMINATION = "missing_termination"
    MISSING_LIABILITY_CAP = "missing_liability_cap"
    MISSING_GOVERNING_LAW = "missing_governing_law"
    MISSING_CONFIDENTIALITY = "missing_confidentiality"


PRESENT_RISKS: frozenset[RiskCode] = frozenset(
    {
        RiskCode.AUTO_RENEWAL,
        RiskCode.UNCAPPED_LIABILITY,
        RiskCode.UNILATERAL_TERMINATION,
        RiskCode.UNLIMITED_INDEMNITY,
    }
)
MISSING_RISKS: frozenset[RiskCode] = frozenset(
    {
        RiskCode.MISSING_TERMINATION,
        RiskCode.MISSING_LIABILITY_CAP,
        RiskCode.MISSING_GOVERNING_LAW,
        RiskCode.MISSING_CONFIDENTIALITY,
    }
)


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Clause(BaseModel):
    """One segmented clause of a contract."""

    index: int = Field(ge=0)
    heading: str
    text: str
    clause_type: ClauseType = ClauseType.OTHER
    type_score: float = 0.0

    model_config = {"frozen": True}


class RiskFinding(BaseModel):
    """A single risk raised about the contract."""

    code: RiskCode
    severity: Severity
    clause_index: int | None = None
    rationale: str = ""

    model_config = {"frozen": True}

    def __hash__(self) -> int:  # findings are compared by code for scoring
        return hash(self.code)


class Report(BaseModel):
    """Full analysis of one contract."""

    clauses: list[Clause] = Field(default_factory=list)
    findings: list[RiskFinding] = Field(default_factory=list)

    @property
    def present_types(self) -> set[ClauseType]:
        return {c.clause_type for c in self.clauses}

    @property
    def risk_codes(self) -> set[RiskCode]:
        return {f.code for f in self.findings}
