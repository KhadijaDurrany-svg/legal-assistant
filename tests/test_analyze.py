from __future__ import annotations

from clausewise.analyze import analyze
from clausewise.models import ClauseType, Report

CONTRACT = """MASTER SERVICES AGREEMENT

1. Term and Renewal
This Agreement shall automatically renew for successive one-year terms.

2. Limitation of Liability
Each party accepts unlimited liability for all damages.

3. Payment
Client shall pay all invoices net 30 days.
"""


def test_analyze_returns_report():
    report = analyze(CONTRACT)
    assert isinstance(report, Report)
    # Title line + three numbered clauses.
    assert len(report.clauses) == 4


def test_clause_indices_sequential():
    report = analyze(CONTRACT)
    assert [c.index for c in report.clauses] == [0, 1, 2, 3]


def test_present_types_include_expected():
    report = analyze(CONTRACT)
    assert ClauseType.TERM in report.present_types
    assert ClauseType.LIABILITY in report.present_types
    assert ClauseType.PAYMENT in report.present_types


def test_analyze_deterministic():
    assert analyze(CONTRACT).model_dump() == analyze(CONTRACT).model_dump()


def test_empty_contract():
    report = analyze("")
    assert report.clauses == []
    # With no clauses at all, protective clauses are reported missing.
    assert report.findings


def test_report_risk_codes_property():
    report = analyze(CONTRACT)
    assert report.risk_codes == {f.code for f in report.findings}
