from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from clausewise.analyze import analyze
from clausewise.generate import (
    _CONFIDENTIALITY,
    _GOVERNING,
    _INDEMNITY,
    _LIABILITY,
    _TERM,
    _TERMINATION,
    generate_contract,
    generate_corpus,
)
from clausewise.models import MISSING_RISKS, PRESENT_RISKS, RiskCode


def test_corpus_reproducible():
    a = generate_corpus(20, seed=1)
    b = generate_corpus(20, seed=1)
    assert [c.text for c in a] == [c.text for c in b]
    assert [c.gold for c in a] == [c.gold for c in b]


def test_different_seed_differs():
    a = generate_corpus(20, seed=1)
    b = generate_corpus(20, seed=2)
    assert [c.text for c in a] != [c.text for c in b]


def test_gold_codes_valid():
    for c in generate_corpus(50, seed=3):
        for code in c.gold:
            assert isinstance(code, RiskCode)


def test_gold_present_and_missing_consistent():
    # A present-risk and its corresponding missing-risk never co-occur.
    for c in generate_corpus(100, seed=5):
        if RiskCode.UNCAPPED_LIABILITY in c.gold:
            assert RiskCode.MISSING_LIABILITY_CAP not in c.gold
        if RiskCode.UNILATERAL_TERMINATION in c.gold:
            assert RiskCode.MISSING_TERMINATION not in c.gold


def test_contract_has_clauses_and_text():
    rng = np.random.default_rng(0)
    c = generate_contract(rng)
    assert c.text.strip()
    assert c.n_clauses >= 1
    assert "MASTER SERVICES AGREEMENT" in c.text


def test_corpus_has_label_variety():
    golds = [c.gold for c in generate_corpus(200, seed=7)]
    seen: set[RiskCode] = set()
    for g in golds:
        seen |= set(g)
    # Every present- and missing-risk should appear somewhere in a large corpus.
    assert PRESENT_RISKS <= seen
    assert MISSING_RISKS <= seen


def test_template_pools_label_balance():
    # Each risk-bearing pool has both risky and safe variants.
    for pool in (_TERM, _LIABILITY, _TERMINATION, _INDEMNITY):
        flags = {risky for _, _, risky in pool}
        assert flags == {True, False}
    # Governing and confidentiality variants are never themselves "risky".
    for pool in (_GOVERNING, _CONFIDENTIALITY):
        assert all(not risky for _, _, risky in pool)


def test_generated_contracts_are_analyzable():
    for c in generate_corpus(30, seed=11):
        report = analyze(c.text)
        assert len(report.clauses) >= 1


@settings(max_examples=30, deadline=None)
@given(st.integers(min_value=0, max_value=10_000))
def test_single_contract_deterministic_per_seed(seed: int):
    a = generate_contract(np.random.default_rng(seed))
    b = generate_contract(np.random.default_rng(seed))
    assert a.text == b.text
    assert a.gold == b.gold
