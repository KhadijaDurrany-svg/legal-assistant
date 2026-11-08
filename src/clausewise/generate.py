"""Seeded synthetic contract generator with ground-truth risk labels.

Each generated contract comes with the exact set of :class:`RiskCode` findings
that are *true* for it, computed from the templates that were chosen, never by
running the detector. That separation is what lets the benchmark measure the
detector honestly.

The phrasing pools are deliberately wider than the detector's cue lexicon and
include three kinds of hard cases:

* **subtle risky** variants that avoid the obvious cue word (drive recall < 1);
* **oddly-worded safe** variants the detector can mistake for risky, or whose
  clause type it misreads (drive precision < 1);
* **decoy** filler clauses (definitions, notices, payment...) that mention risk
  keywords in passing, which a keyword baseline trips over.

No randomness beyond the seeded ``numpy`` generator; no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .models import RiskCode

# A clause template: (heading, body, is_risky). ``is_risky`` is the ground truth
# for the present-risk associated with that clause type.
Template = tuple[str, str, bool]


@dataclass(frozen=True)
class Contract:
    text: str
    gold: frozenset[RiskCode]
    n_clauses: int


# ---------------------------------------------------------------------------
# Phrasing pools. Each list mixes risky and safe variants; the generator picks
# one at random. "subtle"/"odd" comments mark the hard cases.
# ---------------------------------------------------------------------------

_TERM: list[Template] = [
    ("Term and Renewal",
     "This Agreement commences on the Effective Date and shall automatically renew "
     "for successive one-year terms unless either party provides written notice.", True),
    ("Term",
     "The term is evergreen and shall continue in effect indefinitely until terminated "
     "by the parties.", True),
    ("Term",
     "Upon expiration of the Initial Term, this Agreement shall roll over into "
     "additional twelve-month periods on the same terms.", True),
    # subtle risky: no obvious cue word -> detector likely misses (recall < 1)
    ("Term of Agreement",
     "At the close of each period the engagement continues on identical terms for a "
     "further equal period absent written objection from a party.", True),
    ("Term",
     "This Agreement is effective for a fixed term of two years and expires at the end "
     "of that period with no renewal.", False),
    ("Term and Renewal",
     "The initial term is one year and may be renewed only by mutual written agreement "
     "of the parties.", False),
    ("Term",
     "Either party may extend the term by delivering written notice sixty days before "
     "the expiration date.", False),
]

_LIABILITY: list[Template] = [
    ("Limitation of Liability",
     "Each party accepts unlimited liability for all damages arising under or in "
     "connection with this Agreement.", True),
    ("Liability",
     "The Provider shall be fully liable for any and all losses suffered by the Client, "
     "however caused.", True),
    ("Limitation of Liability",
     "In no event shall either party be liable for consequential or indirect damages; "
     "no monetary cap applies to direct damages.", True),
    # odd-worded safe: a real cap the detector may not recognise (precision < 1)
    ("Liability",
     "Total liability of each party is bounded by the fees received in the prior "
     "quarter.", False),
    ("Limitation of Liability",
     "The aggregate liability of either party shall not exceed the total fees paid in "
     "the twelve months preceding the claim.", False),
    ("Limitation of Liability",
     "In no event shall total liability exceed the amounts actually paid under this "
     "Agreement.", False),
    ("Liability",
     "Liability under this Agreement is capped at fifty thousand dollars in the "
     "aggregate.", False),
]

_TERMINATION: list[Template] = [
    ("Termination",
     "The Company may terminate this Agreement at any time for convenience upon thirty "
     "days written notice to the other party.", True),
    ("Termination for Convenience",
     "Provider reserves the right to terminate this Agreement for any reason or no "
     "reason at its sole discretion.", True),
    # subtle risky: one-sided but avoids the "for convenience"/"without cause" cue
    ("Termination",
     "The Vendor may terminate this engagement whenever it chooses, and the Customer "
     "waives any objection to such termination.", True),
    ("Termination",
     "Either party may terminate this Agreement for material breach upon written notice "
     "and a thirty-day cure period.", False),
    ("Termination",
     "Either party may terminate for convenience by giving ninety days written notice.", False),
    ("Termination",
     "This Agreement may be terminated by mutual written consent of both parties.", False),
]

_INDEMNITY: list[Template] = [
    ("Indemnification",
     "The Client shall indemnify and hold harmless the Provider from and against any "
     "and all claims, losses, and damages regardless of cause.", True),
    ("Indemnification",
     "Customer agrees to indemnify Vendor without limitation for all liabilities "
     "arising hereunder.", True),
    ("Indemnification",
     "Each party shall indemnify the other to the extent of claims caused by its own "
     "negligence or breach.", False),
    ("Indemnification",
     "The parties shall mutually indemnify one another for third-party claims.", False),
    ("Indemnification",
     "Provider shall indemnify Client for third-party claims to the extent arising from "
     "Provider's gross negligence.", False),
]

_GOVERNING: list[Template] = [
    ("Governing Law",
     "This Agreement shall be governed by the laws of the State of Delaware.", False),
    ("Governing Law",
     "This Agreement shall be governed by and construed in accordance with the laws of "
     "the State of New York.", False),
    # odd-worded: present but detector may misread the type (false MISSING)
    ("Interpretation",
     "This Agreement is interpreted under New York rules by the parties.", False),
]

_CONFIDENTIALITY: list[Template] = [
    ("Confidentiality",
     "Each party shall keep the other's Confidential Information in confidence and not "
     "disclose it to third parties.", False),
    ("Confidentiality",
     "The receiving party shall protect all proprietary information and trade secrets "
     "of the disclosing party.", False),
    ("Non-Disclosure",
     "Neither party shall use or disclose the other's non-public information except as "
     "permitted herein.", False),
]

# Decoy / filler clauses: never carry a present-risk, but mention risk keywords.
_FILLER: list[Template] = [
    ("Definitions",
     "'Confidential Information' means any non-public information. 'Losses' means all "
     "liabilities, damages, and costs. 'Services' means the work described herein.", False),
    ("Notices",
     "All notices shall be in writing and delivered by certified mail. A party may "
     "terminate a prior notice address by updating it in writing.", False),
    ("Payment",
     "Client shall pay all invoices net 30 days. Late payments accrue interest at one "
     "percent per month.", False),
    ("Warranties",
     "Provider warrants the services will be performed in a professional manner. THE "
     "SERVICES ARE PROVIDED AS IS otherwise.", False),
    ("Force Majeure",
     "Neither party is liable for delays caused by events beyond its reasonable "
     "control, including acts of God.", False),
    ("Dispute Resolution",
     "Any dispute shall be resolved by binding arbitration under the rules of the "
     "American Arbitration Association.", False),
    ("Assignment",
     "Neither party may assign this Agreement without the prior written consent of the "
     "other, except to successors and assigns.", False),
]


@dataclass
class _Spec:
    include_prob: float
    pool: list[Template]
    risk: RiskCode | None  # present-risk this clause can raise
    missing: RiskCode | None  # missing-risk if clause absent
    clauses: list[Template] = field(default_factory=list)


def _pick(rng: np.random.Generator, pool: list[Template]) -> Template:
    return pool[int(rng.integers(len(pool)))]


def generate_contract(rng: np.random.Generator) -> Contract:
    """Generate one labelled synthetic contract."""
    selected: list[Template] = []
    gold: set[RiskCode] = set()

    specs = [
        _Spec(0.82, _TERM, RiskCode.AUTO_RENEWAL, None),
        _Spec(0.72, _LIABILITY, RiskCode.UNCAPPED_LIABILITY, RiskCode.MISSING_LIABILITY_CAP),
        _Spec(0.72, _TERMINATION, RiskCode.UNILATERAL_TERMINATION, RiskCode.MISSING_TERMINATION),
        _Spec(0.62, _INDEMNITY, RiskCode.UNLIMITED_INDEMNITY, None),
        _Spec(0.72, _GOVERNING, None, RiskCode.MISSING_GOVERNING_LAW),
        _Spec(0.72, _CONFIDENTIALITY, None, RiskCode.MISSING_CONFIDENTIALITY),
    ]

    for spec in specs:
        if rng.random() < spec.include_prob:
            heading, body, risky = _pick(rng, spec.pool)
            selected.append((heading, body, risky))
            if risky and spec.risk is not None:
                gold.add(spec.risk)
        elif spec.missing is not None:
            gold.add(spec.missing)

    # Add 2-4 decoy/filler clauses (sampled without replacement).
    n_filler = int(rng.integers(2, 5))
    idx = rng.permutation(len(_FILLER))[:n_filler]
    for i in idx:
        selected.append(_FILLER[int(i)])

    # Shuffle and number the clauses.
    order = rng.permutation(len(selected))
    lines = ["MASTER SERVICES AGREEMENT", ""]
    for n, j in enumerate(order, start=1):
        heading, body, _ = selected[int(j)]
        lines.append(f"{n}. {heading}")
        lines.append(body)
        lines.append("")

    return Contract(text="\n".join(lines).strip() + "\n", gold=frozenset(gold), n_clauses=len(selected))


def generate_corpus(n: int, seed: int) -> list[Contract]:
    """Generate ``n`` contracts deterministically from ``seed``."""
    rng = np.random.default_rng(seed)
    return [generate_contract(rng) for _ in range(n)]
