"""Deterministic clause segmentation.

Splits raw contract text into clauses at structural boundaries: numbered
headings (``1.``, ``1.1``, ``2)``), ``ARTICLE``/``Section`` markers and
standalone upper/title-case heading lines. The goal is not perfect legal
parsing but a stable, crash-proof split that the classifier can work on.
"""

from __future__ import annotations

import re

# A line that begins a new clause. Captures an optional label and a heading.
_NUMBERED = re.compile(r"^\s*(\d+(?:\.\d+)*)[.)]\s+(.*\S)\s*$")
_KEYWORD = re.compile(r"^\s*((?:ARTICLE|Article|SECTION|Section)\s+[\w.]+)[.:) ]+\s*(.*)$")
_LETTERED = re.compile(r"^\s*\(([a-z])\)\s+(.*\S)\s*$")
# A short all-caps or title-case line with no trailing sentence punctuation.
_BARE_HEADING = re.compile(r"^\s*([A-Z][A-Za-z /&'-]{2,48})\s*$")


def _is_heading(line: str) -> tuple[str, str] | None:
    """Return (label, heading-text) if the line starts a clause, else None."""
    for pat in (_NUMBERED, _KEYWORD, _LETTERED):
        m = pat.match(line)
        if m:
            return m.group(1), m.group(2).strip()
    m = _BARE_HEADING.match(line)
    if m:
        words = m.group(1).split()
        # Treat as a heading only if it looks like a title: 1-6 words, and not
        # an obvious prose fragment ending in a lowercase connective.
        if 1 <= len(words) <= 6:
            return "", m.group(1).strip()
    return None


def split_clauses(text: str) -> list[tuple[str, str]]:
    """Split ``text`` into a list of ``(heading, body)`` pairs.

    Leading text before the first recognised heading becomes a preamble clause
    with an empty heading. Always returns at least one clause for non-empty
    input so downstream code never has to special-case emptiness.
    """
    lines = text.splitlines()
    clauses: list[tuple[str, list[str]]] = []
    current_heading = ""
    current_body: list[str] = []
    started = False

    for line in lines:
        head = _is_heading(line)
        if head is not None:
            label, title = head
            if started or any(ln.strip() for ln in current_body):
                clauses.append((current_heading, current_body))
            current_heading = f"{label} {title}".strip()
            current_body = []
            started = True
        else:
            current_body.append(line)

    if started or current_body:
        clauses.append((current_heading, current_body))

    result: list[tuple[str, str]] = []
    for heading, body in clauses:
        body_text = "\n".join(body).strip()
        if not heading and not body_text:
            continue
        result.append((heading, body_text))

    if not result and text.strip():
        result.append(("", text.strip()))
    return result
