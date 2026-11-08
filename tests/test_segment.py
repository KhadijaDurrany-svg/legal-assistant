from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from clausewise.segment import split_clauses

SAMPLE = """MASTER AGREEMENT

1. Definitions
This section defines terms.

2. Term
The term is one year.

3. Governing Law
Governed by Delaware law.
"""


def test_splits_numbered_sections():
    clauses = split_clauses(SAMPLE)
    headings = [h for h, _ in clauses]
    assert "1 Definitions" in headings
    assert "2 Term" in headings
    assert "3 Governing Law" in headings


def test_body_attached_to_heading():
    clauses = dict(split_clauses(SAMPLE))
    assert "one year" in clauses["2 Term"]


def test_keyword_article_heading():
    text = "ARTICLE I Scope\nThe scope is defined here.\nSection 2: Fees\nFees are due."
    headings = [h for h, _ in split_clauses(text)]
    assert any("ARTICLE" in h for h in headings)
    assert any("Section 2" in h for h in headings)


def test_lettered_subclause():
    text = "(a) First point here.\n(b) Second point here."
    clauses = split_clauses(text)
    assert len(clauses) == 2


def test_empty_text_returns_empty():
    assert split_clauses("") == []
    assert split_clauses("   \n  \n") == []


def test_preamble_before_first_heading_kept():
    text = "Some intro prose.\n1. Clause\nBody."
    clauses = split_clauses(text)
    assert clauses[0][0] == ""
    assert "intro" in clauses[0][1]


def test_text_without_headings_is_one_clause():
    text = "just a paragraph of running text with no structure at all here now."
    clauses = split_clauses(text)
    assert len(clauses) == 1


@given(st.text())
def test_never_crashes_on_arbitrary_text(text: str):
    result = split_clauses(text)
    assert isinstance(result, list)
    for heading, body in result:
        assert isinstance(heading, str)
        assert isinstance(body, str)


@given(st.text(min_size=1).filter(lambda s: s.strip()))
def test_nonempty_input_yields_at_least_one_clause(text: str):
    assert len(split_clauses(text)) >= 1
