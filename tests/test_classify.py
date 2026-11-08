from __future__ import annotations

import pytest

from clausewise.classify import classify_clause, score_clause
from clausewise.models import ClauseType


@pytest.mark.parametrize(
    "heading,body,expected",
    [
        ("Termination", "Either party may terminate for material breach.", ClauseType.TERMINATION),
        ("Limitation of Liability", "Aggregate liability shall not exceed fees.", ClauseType.LIABILITY),
        ("Indemnification", "Client shall indemnify and hold harmless Provider.", ClauseType.INDEMNIFICATION),
        ("Confidentiality", "Keep Confidential Information in confidence.", ClauseType.CONFIDENTIALITY),
        ("Governing Law", "Governed by the laws of the State of New York.", ClauseType.GOVERNING_LAW),
        ("Term and Renewal", "The initial term is one year and may renew.", ClauseType.TERM),
        ("Payment", "Client shall pay all invoices net 30 days.", ClauseType.PAYMENT),
        ("Force Majeure", "Neither party liable for force majeure events.", ClauseType.FORCE_MAJEURE),
        ("Dispute Resolution", "Disputes resolved by binding arbitration.", ClauseType.DISPUTE_RESOLUTION),
        ("Assignment", "Neither party may assign without consent.", ClauseType.ASSIGNMENT),
    ],
)
def test_classifies_common_clauses(heading, body, expected):
    ctype, score = classify_clause(heading, body)
    assert ctype == expected
    assert score > 0


def test_unrelated_text_is_other():
    ctype, _ = classify_clause("Preamble", "This document was drafted on a Tuesday in spring.")
    assert ctype == ClauseType.OTHER


def test_score_below_threshold_is_other():
    # A single weak cue should not clear the threshold on its own.
    ctype, score = classify_clause("", "The fees are described elsewhere.")
    assert ctype == ClauseType.OTHER


def test_heading_boosts_score():
    with_heading = classify_clause("Termination", "Either party may act.")[1]
    without_heading = classify_clause("", "Either party may act.")[1]
    assert with_heading >= without_heading


def test_score_clause_returns_mapping():
    scores = score_clause("Termination", "terminate for cause")
    assert ClauseType.TERMINATION in scores
    assert all(v > 0 for v in scores.values())


def test_terminated_past_tense_matches():
    # Regression: 'terminated' must register as a termination cue.
    ctype, _ = classify_clause("Termination", "This Agreement may be terminated by notice.")
    assert ctype == ClauseType.TERMINATION


def test_deterministic():
    a = classify_clause("Liability", "liability is capped at fees paid")
    b = classify_clause("Liability", "liability is capped at fees paid")
    assert a == b
