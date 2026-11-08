"""Cue lexicons used by the deterministic classifier and risk rules.

These weights are the project's "knowledge". They were written by hand from
common contract phrasings and are *independent* of the synthetic generator's
templates (the generator in :mod:`clausewise.generate` draws from its own,
deliberately wider, phrasing pools). Keeping the two apart is what makes the
benchmark non-trivial: the classifier cannot simply memorise the generator.
"""

from __future__ import annotations

import re

from .models import ClauseType

# Each cue is (compiled regex, weight). Scores for a clause are summed per type.
_RAW_CUES: dict[ClauseType, list[tuple[str, float]]] = {
    ClauseType.TERM: [
        (r"\bterm of this agreement\b", 3.0),
        (r"\binitial term\b", 2.5),
        (r"\brenew\w*\b", 2.0),
        (r"\beffective date\b", 1.5),
        (r"\bexpir\w*\b", 1.5),
        (r"\bsuccessive\b", 1.5),
        (r"\bevergreen\b", 3.0),
    ],
    ClauseType.TERMINATION: [
        (r"\bterminat\w*\b", 3.0),
        (r"\bfor convenience\b", 2.0),
        (r"\bfor cause\b", 1.5),
        (r"\bupon .{0,20}notice\b", 1.0),
        (r"\bmaterial breach\b", 1.5),
    ],
    ClauseType.LIABILITY: [
        (r"\bliabilit(y|ies)\b", 3.0),
        (r"\blimitation of liability\b", 3.0),
        (r"\bconsequential damages\b", 1.5),
        (r"\baggregate\b", 1.0),
        (r"\bin no event\b", 1.5),
    ],
    ClauseType.INDEMNIFICATION: [
        (r"\bindemnif\w*\b", 3.0),
        (r"\bhold harmless\b", 2.5),
        (r"\bdefend\b", 1.0),
        (r"\bthird[- ]party claims?\b", 1.5),
    ],
    ClauseType.CONFIDENTIALITY: [
        (r"\bconfidential\w*\b", 3.0),
        (r"\bnon[- ]disclosure\b", 2.5),
        (r"\bproprietary information\b", 2.0),
        (r"\btrade secrets?\b", 1.5),
    ],
    ClauseType.GOVERNING_LAW: [
        (r"\bgoverning law\b", 3.0),
        (r"\bgoverned by the laws\b", 3.0),
        (r"\bconstrued in accordance with\b", 2.0),
        (r"\bjurisdiction\b", 1.0),
        (r"\blaws of the state of\b", 2.0),
    ],
    ClauseType.PAYMENT: [
        (r"\bpayment\b", 2.0),
        (r"\binvoice(s|d)?\b", 2.0),
        (r"\bfees?\b", 1.5),
        (r"\bnet (?:15|30|45|60) days\b", 2.0),
        (r"\blate (?:fee|charge|payment)\b", 1.5),
    ],
    ClauseType.ASSIGNMENT: [
        (r"\bassign\w*\b", 3.0),
        (r"\bsuccessors and assigns\b", 2.0),
        (r"\btransfer .{0,20}rights\b", 1.0),
    ],
    ClauseType.FORCE_MAJEURE: [
        (r"\bforce majeure\b", 3.0),
        (r"\bacts? of god\b", 2.5),
        (r"\bbeyond .{0,20}reasonable control\b", 2.0),
    ],
    ClauseType.WARRANTY: [
        (r"\bwarrant\w*\b", 3.0),
        (r"\bas is\b", 1.5),
        (r"\bmerchantability\b", 2.0),
        (r"\bfitness for a particular purpose\b", 2.0),
    ],
    ClauseType.DISPUTE_RESOLUTION: [
        (r"\barbitration\b", 3.0),
        (r"\bmediation\b", 2.0),
        (r"\bdispute resolution\b", 3.0),
        (r"\bbinding arbitration\b", 2.5),
    ],
    ClauseType.DEFINITIONS: [
        (r"\bdefinitions\b", 3.0),
        (r'\bmeans\b', 1.0),
        (r'\bshall have the meaning\b', 2.0),
    ],
    ClauseType.NOTICES: [
        (r"\bnotices?\b", 2.0),
        (r"\bin writing and (?:delivered|sent)\b", 1.5),
        (r"\bcertified mail\b", 2.0),
    ],
}

CUES: dict[ClauseType, list[tuple[re.Pattern[str], float]]] = {
    ctype: [(re.compile(pat, re.IGNORECASE), w) for pat, w in pairs]
    for ctype, pairs in _RAW_CUES.items()
}

# Minimum score for a clause to be assigned a type instead of OTHER.
TYPE_THRESHOLD: float = 2.5
