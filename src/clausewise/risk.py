"""Deterministic risk flagging over classified clauses.

Two families of findings:

* **present risks** — a clause is in the document and is risky as written
  (auto-renewal, uncapped liability, one-sided termination-for-convenience,
  unlimited/one-sided indemnity);
* **missing risks** — a protective clause that ought to be present is absent.

The rules deliberately handle negation and qualification (a liability clause
that *does* cap damages is not flagged; a term clause that explicitly does not
auto-renew is not flagged). That is where the edge over a keyword baseline
comes from, and it is also why detection is strong but not perfect.
"""

from __future__ import annotations

import re

from .models import Clause, ClauseType, RiskCode, RiskFinding, Severity

# ---------------------------------------------------------------------------
# Signal patterns (compiled once).
# ---------------------------------------------------------------------------

_AUTO_RENEW = re.compile(
    r"\b(?:automatically renew|automatically extend|renew(?:s|ed)? automatically"
    r"|evergreen|renew(?:s)? for successive|successive .{0,20}renewal"
    r"|roll(?:s)? over|continue(?:s)? (?:in effect )?(?:thereafter|indefinitely))\b"
    r"|renew(?:s|ed)?\b(?=.{0,60}\bunless\b)",
    re.IGNORECASE | re.DOTALL,
)
_RENEW_NEGATED = re.compile(
    r"\b(?:not|no)\b.{0,25}\b(?:renew|extend)"
    r"|\b(?:renew|extend)\w*\b.{0,15}\bonly\b.{0,25}\b(?:written|mutual) (?:consent|agreement)\b"
    r"|\bshall not .{0,15}renew\b|\bwill not .{0,15}renew\b|\bdoes not .{0,15}renew\b",
    re.IGNORECASE | re.DOTALL,
)

_LIAB_CAP = re.compile(
    r"\b(?:shall not exceed|not to exceed|limited to|capped at|maximum .{0,15}liability"
    r"|aggregate liability .{0,40}(?:exceed|equal)|total liability .{0,40}exceed"
    r"|in no event .{0,60}(?:exceed|greater than))\b",
    re.IGNORECASE | re.DOTALL,
)
_LIAB_UNLIMITED = re.compile(
    r"\b(?:unlimited liability|liability .{0,20}not .{0,10}limited"
    r"|without (?:any )?limitation .{0,20}liability|no (?:cap|limit) on .{0,15}liability"
    r"|fully liable for (?:any|all))\b",
    re.IGNORECASE | re.DOTALL,
)

_FOR_CONVENIENCE = re.compile(
    r"\b(?:for convenience|without cause|for any reason or no reason"
    r"|at any time .{0,25}(?:without|no) (?:cause|reason)|at its (?:sole )?discretion)\b",
    re.IGNORECASE | re.DOTALL,
)
_BILATERAL = re.compile(
    r"\b(?:either party|both parties|each party|any party)\b", re.IGNORECASE
)

_INDEMNITY_BROAD = re.compile(
    r"\b(?:any and all|without limitation|from and against all"
    r"|all (?:claims|losses|damages|liabilities)|regardless of .{0,20}(?:fault|cause))\b",
    re.IGNORECASE | re.DOTALL,
)
_INDEMNITY_SAFE = re.compile(
    r"\b(?:mutual(?:ly)? indemnif|each party (?:shall|will|agrees to) indemnif"
    r"|indemn'?ification .{0,40}(?:capped|limited|not exceed)"
    r"|to the extent (?:caused|arising) .{0,30}(?:negligence|breach))\b",
    re.IGNORECASE | re.DOTALL,
)

_SEVERITY: dict[RiskCode, Severity] = {
    RiskCode.AUTO_RENEWAL: Severity.MEDIUM,
    RiskCode.UNCAPPED_LIABILITY: Severity.HIGH,
    RiskCode.UNILATERAL_TERMINATION: Severity.MEDIUM,
    RiskCode.UNLIMITED_INDEMNITY: Severity.HIGH,
    RiskCode.MISSING_TERMINATION: Severity.MEDIUM,
    RiskCode.MISSING_LIABILITY_CAP: Severity.HIGH,
    RiskCode.MISSING_GOVERNING_LAW: Severity.MEDIUM,
    RiskCode.MISSING_CONFIDENTIALITY: Severity.LOW,
}


def _finding(code: RiskCode, idx: int | None, why: str) -> RiskFinding:
    return RiskFinding(code=code, severity=_SEVERITY[code], clause_index=idx, rationale=why)


def flag_risks(clauses: list[Clause]) -> list[RiskFinding]:
    """Return the risk findings for a classified contract.

    At most one finding per :class:`RiskCode` is returned (the first clause
    that triggers it), matching how the benchmark scores findings as a set.
    """
    findings: list[RiskFinding] = []
    seen: set[RiskCode] = set()
    present = {c.clause_type for c in clauses}

    def add(code: RiskCode, idx: int | None, why: str) -> None:
        if code not in seen:
            findings.append(_finding(code, idx, why))
            seen.add(code)

    for clause in clauses:
        body = clause.text
        ct = clause.clause_type

        if ct == ClauseType.TERM and _AUTO_RENEW.search(body) and not _RENEW_NEGATED.search(body):
            add(RiskCode.AUTO_RENEWAL, clause.index, "term auto-renews with no opt-out language")

        if ct == ClauseType.LIABILITY:
            if _LIAB_UNLIMITED.search(body):
                add(RiskCode.UNCAPPED_LIABILITY, clause.index, "liability stated as unlimited")
            elif not _LIAB_CAP.search(body):
                add(RiskCode.UNCAPPED_LIABILITY, clause.index, "liability clause states no cap")

        if (
            ct == ClauseType.TERMINATION
            and _FOR_CONVENIENCE.search(body)
            and not _BILATERAL.search(body)
        ):
            add(
                RiskCode.UNILATERAL_TERMINATION,
                clause.index,
                "termination for convenience granted to one party only",
            )

        if (
            ct == ClauseType.INDEMNIFICATION
            and _INDEMNITY_BROAD.search(body)
            and not _INDEMNITY_SAFE.search(body)
        ):
            add(
                RiskCode.UNLIMITED_INDEMNITY,
                clause.index,
                "indemnity is broad and neither mutual nor capped",
            )

    # Missing-clause risks.
    if ClauseType.TERMINATION not in present:
        add(RiskCode.MISSING_TERMINATION, None, "no termination clause found")
    if ClauseType.GOVERNING_LAW not in present:
        add(RiskCode.MISSING_GOVERNING_LAW, None, "no governing-law clause found")
    if ClauseType.CONFIDENTIALITY not in present:
        add(RiskCode.MISSING_CONFIDENTIALITY, None, "no confidentiality clause found")
    if ClauseType.LIABILITY not in present:
        add(RiskCode.MISSING_LIABILITY_CAP, None, "no limitation-of-liability clause found")

    return findings
