"""Scoring: precision/recall/F1, bootstrap CIs and a paired permutation test.

Findings are scored as sets per contract. The headline metric is *micro*
precision/recall/F1 over all ``(contract, risk_code)`` pairs in the corpus.
Uncertainty on micro-F1 comes from a contract-level bootstrap. Significance of
the gap between two detectors comes from a paired permutation test on
per-contract F1, which makes no distributional assumption.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .models import RiskCode


@dataclass(frozen=True)
class PRF:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int


def _prf(tp: int, fp: int, fn: int) -> PRF:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return PRF(precision, recall, f1, tp, fp, fn)


def confusion(pred: set[RiskCode], gold: set[RiskCode]) -> tuple[int, int, int]:
    """Return ``(tp, fp, fn)`` for one contract."""
    tp = len(pred & gold)
    fp = len(pred - gold)
    fn = len(gold - pred)
    return tp, fp, fn


def micro_prf(preds: list[set[RiskCode]], golds: list[set[RiskCode]]) -> PRF:
    """Micro-averaged precision/recall/F1 over the whole corpus."""
    tp = fp = fn = 0
    for pred, gold in zip(preds, golds, strict=True):
        a, b, c = confusion(pred, gold)
        tp += a
        fp += b
        fn += c
    return _prf(tp, fp, fn)


def per_contract_f1(preds: list[set[RiskCode]], golds: list[set[RiskCode]]) -> np.ndarray:
    """F1 of each contract (used for the paired significance test).

    A contract with no gold and no predicted findings scores 1.0 (the detector
    was correct to stay silent).
    """
    out = np.empty(len(preds), dtype=float)
    for i, (pred, gold) in enumerate(zip(preds, golds, strict=True)):
        tp, fp, fn = confusion(pred, gold)
        if tp + fp + fn == 0:
            out[i] = 1.0
        else:
            denom = 2 * tp + fp + fn
            out[i] = (2 * tp / denom) if denom else 0.0
    return out


def bootstrap_f1_ci(
    preds: list[set[RiskCode]],
    golds: list[set[RiskCode]],
    n_boot: int,
    seed: int,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Percentile bootstrap CI for micro-F1, resampling contracts."""
    rng = np.random.default_rng(seed)
    n = len(preds)
    tps = np.array([confusion(p, g)[0] for p, g in zip(preds, golds, strict=True)])
    fps = np.array([confusion(p, g)[1] for p, g in zip(preds, golds, strict=True)])
    fns = np.array([confusion(p, g)[2] for p, g in zip(preds, golds, strict=True)])
    stats = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        tp = int(tps[idx].sum())
        fp = int(fps[idx].sum())
        fn = int(fns[idx].sum())
        stats[b] = _prf(tp, fp, fn).f1
    lo = float(np.quantile(stats, alpha / 2))
    hi = float(np.quantile(stats, 1 - alpha / 2))
    return lo, hi


def paired_permutation_pvalue(
    preds_a: list[set[RiskCode]],
    preds_b: list[set[RiskCode]],
    golds: list[set[RiskCode]],
    n_perm: int,
    seed: int,
) -> tuple[float, float]:
    """Two-sided paired permutation test on per-contract F1 (a vs b).

    Returns ``(observed_mean_difference, p_value)``. Under the null the two
    detectors' per-contract scores are exchangeable, so each permutation flips
    a random subset of the paired differences' signs.
    """
    fa = per_contract_f1(preds_a, golds)
    fb = per_contract_f1(preds_b, golds)
    diff = fa - fb
    observed = float(diff.mean())
    rng = np.random.default_rng(seed)
    n = len(diff)
    count = 0
    abs_obs = abs(observed)
    for _ in range(n_perm):
        signs = rng.integers(0, 2, size=n) * 2 - 1  # +1 / -1
        if abs(float((diff * signs).mean())) >= abs_obs - 1e-12:
            count += 1
    pvalue = (count + 1) / (n_perm + 1)  # add-one smoothing
    return observed, pvalue
