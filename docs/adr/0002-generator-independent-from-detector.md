# 2. The synthetic generator is kept independent of the detector

Status: accepted

## Context

The benchmark scores the detector on synthetic contracts. The failure mode of
any synthetic benchmark is circularity: if the generator writes clauses using
the exact phrases the detector looks for, detection is trivially perfect and
the numbers mean nothing.

## Decision

The generator (`generate.py`) and the detector (`cues.py`, `risk.py`) are
written from *separate* phrasing pools, and the generator deliberately includes
hard cases:

* **subtle risky** variants that express a risk without the obvious cue word
  (e.g. a term that "continues on identical terms for a further equal period"
  with no "renew"/"evergreen"), which the detector under-recalls;
* **oddly-worded safe** variants that the detector can misread — a real
  liability cap phrased as "bounded by the fees received in the prior quarter",
  or a governing-law clause headed "Interpretation" — which cost precision;
* **decoy** filler clauses (definitions, notices, payment) that mention risk
  keywords in passing, which the keyword baseline trips over but the typed
  detector does not.

Ground truth is computed from *which template was chosen*, never by running the
detector on the text.

## Consequences

* The measured F1 for our detector is strong but clearly below 1.0, and the
  precision/recall split is explained entirely by the designed hard cases (see
  the error breakdown in the README).
* A `test_bench.py` honesty guard asserts the detector's F1, precision and
  recall are each strictly below 1.0 on the synthetic corpus. If a future
  change makes detection look perfect, the test fails and the generator must be
  hardened rather than the result shipped.
* The benchmark measures generalisation to unseen phrasing, not memorisation.
