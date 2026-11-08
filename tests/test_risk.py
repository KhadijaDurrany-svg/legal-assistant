from __future__ import annotations

from clausewise.analyze import analyze
from clausewise.models import ClauseType, RiskCode
from clausewise.risk import flag_risks


def codes(text: str) -> set[RiskCode]:
    return analyze(text).risk_codes


def test_auto_renewal_flagged():
    text = "1. Term\nThis Agreement shall automatically renew for successive one-year terms."
    assert RiskCode.AUTO_RENEWAL in codes(text)


def test_fixed_term_not_flagged():
    text = (
        "1. Term\nThis Agreement is for a fixed term of two years with no renewal.\n"
        "2. Termination\nEither party may terminate for cause.\n"
        "3. Governing Law\nGoverned by Delaware law.\n"
        "4. Confidentiality\nKeep information confidential.\n"
        "5. Liability\nLiability shall not exceed fees paid."
    )
    assert RiskCode.AUTO_RENEWAL not in codes(text)


def test_unlimited_liability_flagged():
    text = "1. Limitation of Liability\nEach party accepts unlimited liability for all damages."
    assert RiskCode.UNCAPPED_LIABILITY in codes(text)


def test_uncapped_liability_flagged_when_no_cap():
    text = "1. Liability\nThe parties acknowledge their liability for damages under this Agreement."
    assert RiskCode.UNCAPPED_LIABILITY in codes(text)


def test_capped_liability_not_flagged():
    text = "1. Limitation of Liability\nAggregate liability shall not exceed the fees paid in the prior year."
    assert RiskCode.UNCAPPED_LIABILITY not in codes(text)


def test_unilateral_termination_flagged():
    text = "1. Termination\nThe Company may terminate this Agreement at any time for convenience."
    assert RiskCode.UNILATERAL_TERMINATION in codes(text)


def test_bilateral_convenience_not_flagged():
    text = "1. Termination\nEither party may terminate for convenience on ninety days notice."
    assert RiskCode.UNILATERAL_TERMINATION not in codes(text)


def test_broad_indemnity_flagged():
    text = "1. Indemnification\nClient shall indemnify Provider from any and all claims regardless of cause."
    assert RiskCode.UNLIMITED_INDEMNITY in codes(text)


def test_mutual_indemnity_not_flagged():
    text = "1. Indemnification\nThe parties shall mutually indemnify one another for third-party claims."
    assert RiskCode.UNLIMITED_INDEMNITY not in codes(text)


def test_missing_termination():
    text = (
        "1. Governing Law\nGoverned by Delaware law.\n"
        "2. Confidentiality\nKeep it confidential.\n"
        "3. Liability\nLiability shall not exceed fees."
    )
    assert RiskCode.MISSING_TERMINATION in codes(text)


def test_missing_governing_law():
    text = (
        "1. Termination\nEither party may terminate for cause.\n"
        "2. Confidentiality\nKeep it confidential.\n"
        "3. Liability\nLiability shall not exceed fees."
    )
    assert RiskCode.MISSING_GOVERNING_LAW in codes(text)


def test_missing_confidentiality():
    text = (
        "1. Termination\nEither party may terminate for cause.\n"
        "2. Governing Law\nGoverned by Delaware law.\n"
        "3. Liability\nLiability shall not exceed fees."
    )
    assert RiskCode.MISSING_CONFIDENTIALITY in codes(text)


def test_missing_liability_cap_when_no_liability_clause():
    text = (
        "1. Termination\nEither party may terminate for cause.\n"
        "2. Governing Law\nGoverned by Delaware law.\n"
        "3. Confidentiality\nKeep it confidential."
    )
    found = codes(text)
    assert RiskCode.MISSING_LIABILITY_CAP in found
    # If there is no liability clause at all, we do not also raise UNCAPPED.
    assert RiskCode.UNCAPPED_LIABILITY not in found


def test_present_liability_gives_uncapped_not_missing():
    text = "1. Liability\nThe parties accept liability for all damages without limit."
    found = codes(text)
    assert RiskCode.UNCAPPED_LIABILITY in found
    assert RiskCode.MISSING_LIABILITY_CAP not in found


def test_at_most_one_finding_per_code():
    text = "1. Liability\nUnlimited liability.\n2. Liability\nAlso unlimited liability here."
    findings = [f for f in analyze(text).findings if f.code == RiskCode.UNCAPPED_LIABILITY]
    assert len(findings) == 1


def test_flag_risks_on_empty_list():
    # No clauses at all -> everything protective is missing.
    findings = flag_risks([])
    found = {f.code for f in findings}
    assert RiskCode.MISSING_TERMINATION in found
    assert RiskCode.MISSING_GOVERNING_LAW in found


def test_findings_carry_severity_and_rationale():
    text = "1. Liability\nUnlimited liability for all damages."
    f = next(f for f in analyze(text).findings if f.code == RiskCode.UNCAPPED_LIABILITY)
    assert f.severity.value in {"low", "medium", "high"}
    assert f.rationale


def test_renewal_negation_not_flagged():
    text = "1. Term\nThe term is one year and may be renewed only by mutual written agreement."
    assert RiskCode.AUTO_RENEWAL not in codes(text)


def test_non_liability_type_does_not_trigger_uncapped():
    # A definitions clause mentioning liabilities must not raise a liability risk.
    text = (
        "1. Definitions\n'Losses' means all liabilities and damages suffered by a party.\n"
        "2. Liability\nLiability shall not exceed fees."
    )
    report = analyze(text)
    defn = report.clauses[0]
    assert defn.clause_type != ClauseType.LIABILITY
