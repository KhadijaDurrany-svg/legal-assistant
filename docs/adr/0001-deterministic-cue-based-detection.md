# 1. Deterministic cue-based detection, not an ML model or LLM

Status: accepted

## Context

The task is to find risky and missing clauses in contracts. The obvious
industry approach is to send the document to a large language model. That makes
the tool non-reproducible (model versions drift), non-offline (keys, network,
cost) and unmeasurable (no stable ground truth to score against).

We want a tool that runs with no network, no keys and no downloads, gives the
same answer every time, and whose quality can be stated as a number.

## Decision

Detection is fully deterministic and local:

1. **Segment** the contract into clauses at structural boundaries
   (`segment.py`).
2. **Classify** each clause into a type by summing hand-written weighted cue
   matches, with a threshold below which a clause is `OTHER` (`classify.py`,
   `cues.py`).
3. **Flag risks** with explicit rules over the typed clauses, including
   negation and scope handling — a liability clause that caps damages is not
   flagged; a term that explicitly does not renew is not flagged (`risk.py`).

No learned weights, no embeddings, no probabilistic inference at run time. The
only randomness in the whole package is the *seeded* synthetic data generator
and the bootstrap/permutation resampling in the benchmark.

## Consequences

* Reproducible and offline by construction; the dependency set is `numpy` and
  `pydantic` only.
* The ceiling is lower than a good LLM's: non-standard phrasing is missed. We
  accept that and measure it honestly (see ADR 0002, ADR 0003) rather than hide
  it. The "Known gaps" section of the README lists the concrete failure modes.
* Every finding carries a rationale, so a reviewer can see *why* a clause was
  flagged — something an opaque model does not give.
