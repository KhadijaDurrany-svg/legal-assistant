from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from clausewise.metrics import (
    bootstrap_f1_ci,
    confusion,
    micro_prf,
    paired_permutation_pvalue,
    per_contract_f1,
)
from clausewise.models import RiskCode

A = RiskCode.AUTO_RENEWAL
B = RiskCode.UNCAPPED_LIABILITY
C = RiskCode.MISSING_TERMINATION


def test_confusion_basic():
    assert confusion({A, B}, {A, C}) == (1, 1, 1)


def test_perfect_prediction():
    golds = [{A, B}, {C}]
    prf = micro_prf(golds, golds)
    assert prf.precision == 1.0
    assert prf.recall == 1.0
    assert prf.f1 == 1.0


def test_empty_prediction_zero_recall():
    prf = micro_prf([set(), set()], [{A}, {B}])
    assert prf.recall == 0.0
    assert prf.f1 == 0.0


def test_f1_between_zero_and_one():
    preds = [{A}, {A, B}, set()]
    golds = [{A, B}, {A}, {C}]
    prf = micro_prf(preds, golds)
    assert 0.0 <= prf.f1 <= 1.0


def test_per_contract_f1_silent_correct_is_one():
    scores = per_contract_f1([set()], [set()])
    assert scores[0] == 1.0


def test_per_contract_f1_length():
    preds = [{A}, {B}, set()]
    golds = [{A}, set(), {C}]
    assert len(per_contract_f1(preds, golds)) == 3


def test_bootstrap_ci_ordering_and_range():
    preds = [{A}, {A, B}, {C}, set(), {A}]
    golds = [{A, B}, {A}, {C}, {B}, {A}]
    lo, hi = bootstrap_f1_ci(preds, golds, n_boot=200, seed=0)
    assert 0.0 <= lo <= hi <= 1.0


def test_permutation_identical_systems_high_p():
    preds = [{A}, {B}, {C}]
    golds = [{A, B}, {B}, set()]
    obs, p = paired_permutation_pvalue(preds, preds, golds, n_perm=500, seed=0)
    assert obs == 0.0
    assert p == 1.0


def test_permutation_pvalue_in_unit_interval():
    better = [{A, B}, {C}, {A}]
    worse = [set(), set(), set()]
    golds = [{A, B}, {C}, {A}]
    obs, p = paired_permutation_pvalue(better, worse, golds, n_perm=1000, seed=1)
    assert obs > 0
    assert 0.0 < p <= 1.0


@settings(max_examples=40, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.sets(st.sampled_from([A, B, C])),
            st.sets(st.sampled_from([A, B, C])),
        ),
        min_size=1,
        max_size=15,
    )
)
def test_micro_prf_invariants(pairs):
    preds = [p for p, _ in pairs]
    golds = [g for _, g in pairs]
    prf = micro_prf(preds, golds)
    assert 0.0 <= prf.precision <= 1.0
    assert 0.0 <= prf.recall <= 1.0
    assert 0.0 <= prf.f1 <= 1.0
    assert prf.tp >= 0 and prf.fp >= 0 and prf.fn >= 0
