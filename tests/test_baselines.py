from __future__ import annotations

from clausewise.baselines import RandomDetector, detect_ours, keyword_detector
from clausewise.models import RiskCode


def test_keyword_flags_on_keyword_presence():
    text = "1. Term\nThis Agreement shall renew automatically."
    assert RiskCode.AUTO_RENEWAL in keyword_detector(text)


def test_keyword_false_positive_on_decoy():
    # 'liability' appears only in a definitions decoy, but keyword flags uncapped.
    text = "1. Definitions\n'Losses' means all liabilities and damages."
    assert RiskCode.UNCAPPED_LIABILITY in keyword_detector(text)


def test_keyword_missing_logic():
    text = "1. Payment\nFees are due net 30."
    found = keyword_detector(text)
    assert RiskCode.MISSING_GOVERNING_LAW in found
    assert RiskCode.MISSING_CONFIDENTIALITY in found


def test_random_detector_reproducible():
    a = RandomDetector(seed=42)
    b = RandomDetector(seed=42)
    texts = ["a", "b", "c"]
    assert [a(t) for t in texts] == [b(t) for t in texts]


def test_random_detector_returns_valid_codes():
    det = RandomDetector(seed=1, p=0.5)
    out = det("anything")
    assert out <= set(RiskCode)


def test_detect_ours_matches_analyze():
    from clausewise.analyze import analyze

    text = "1. Liability\nUnlimited liability for all damages."
    assert detect_ours(text) == analyze(text).risk_codes
    assert RiskCode.UNCAPPED_LIABILITY in detect_ours(text)
