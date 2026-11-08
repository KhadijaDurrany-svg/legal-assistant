# clausewise

Offline, deterministic **contract clause extractor and risk flagger**. Given a
contract as plain text, clausewise segments it into clauses, classifies each
clause by type, and flags two kinds of risk:

* **present risks** — a clause that is in the document and risky as written:
  auto-renewal, uncapped liability, one-sided termination-for-convenience,
  unlimited/one-sided indemnity;
* **missing risks** — a protective clause that ought to be there and isn't:
  no termination clause, no limitation-of-liability, no governing-law, no
  confidentiality.

It ships with a **reproducible benchmark** that measures how well the flagger
detects injected risky/missing clauses against two baselines (keyword-only and
random), with bootstrap confidence intervals and a paired permutation test.

No network. No API keys. No model downloads. Dependencies are `numpy` and
`pydantic` only. Every risk a sentence finds comes with a rationale, and every
number in this README comes from a command you can re-run.

> clausewise is a drafting aid, not legal advice. It uses hand-written rules,
> misses non-standard phrasing (see **Known gaps**), and does not replace a
> qualified lawyer's review.

## How this differs from an LLM legal-assistant agent

This project was built deliberately distinct from the common "legal assistant
agent" design (an LLM behind a service and/or an MCP server that answers
free-text legal tasks). The differences are structural, not cosmetic:

| | LLM legal-assistant agent | clausewise |
|---|---|---|
| Core | prompt + hosted model (+ optional MCP server / HTTP API) | hand-written deterministic rules |
| Network / keys | required (provider API key) | none — fully offline |
| Reproducibility | varies with model version and sampling | identical output every run |
| Interface | agent tools / server endpoints | a library + a local CLI (no server, no MCP) |
| Quality claim | typically unmeasured | micro-P/R/F1 vs baselines, CIs, permutation p |
| Explainability | opaque generation | per-finding rationale and clause index |

clausewise is a focused analyzer with a measured quality number, not a
general-purpose agent.

## Results

Real run on the default synthetic corpus (`clausewise bench`, 400 contracts,
seed 7, 2000 bootstrap resamples, 10000 permutations). Reproduced in
`benchmarks/results.json`.

Detection of risk findings — micro-averaged over all `(contract, risk_code)`
pairs:

| detector | precision | recall | F1 | F1 95% CI |
|---|---|---|---|---|
| **ours** | **0.865** | **0.889** | **0.877** | [0.862, 0.892] |
| keyword-only | 0.475 | 0.713 | 0.571 | [0.547, 0.593] |
| random (p=0.5) | 0.308 | 0.498 | 0.381 | [0.358, 0.404] |

Significance (paired permutation test on per-contract F1):

| comparison | micro-F1 Δ | mean per-contract F1 Δ | p-value |
|---|---|---|---|
| ours − keyword-only | +0.306 | +0.305 | 0.0001 |
| ours − random | +0.496 | +0.496 | 0.0001 |

`p = 0.0001` is the resolution floor `1 / (n_perm + 1)`: across 10000
permutations none reached the observed gap. It is reported as the floor, not
rounded to zero.

### Where the errors are (why F1 is 0.877, not 1.0)

On the default corpus (990 gold findings) our detector makes 110 false
negatives and 137 false positives, all traceable to the generator's designed
hard cases:

| error | count | cause |
|---|---|---|
| FN `auto_renewal` | 52 | a renewal written without any renewal cue ("continues ... for a further equal period") |
| FN `unilateral_termination` | 58 | one-sided termination that avoids the "for convenience"/"without cause" cue |
| FP `missing_governing_law` | 97 | a governing-law clause headed "Interpretation" is classified `OTHER`, so the clause is reported missing |
| FP `uncapped_liability` | 40 | a genuine cap phrased unusually ("bounded by the fees received in the prior quarter") is not recognised as a cap |

These are honest limitations of cue-based detection, not benchmark noise. See
**Known gaps**.

## Install

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"   # drop [dev] for runtime only
```

Requires Python 3.10+.

## Use

Run the benchmark (writes `benchmarks/results.json` and
`benchmarks/manifest.json`):

```bash
clausewise bench                 # defaults: 400 contracts, seed 7
clausewise bench --no-write      # print only, write nothing
clausewise bench --n 1000 --seed 3
```

Flag risks in your own contract text file:

```bash
clausewise review path/to/contract.txt
```

Example output:

```
4 clause(s):
  [0] 1 Termination  ->  termination (score 10.5)
  [1] 2 Limitation of Liability  ->  liability (score 13.5)
  ...
2 risk finding(s):
  [  high] uncapped_liability       (clause 1): liability stated as unlimited
  [medium] unilateral_termination   (clause 0): termination for convenience granted to one party only
```

As a library:

```python
from clausewise import analyze

report = analyze(open("contract.txt").read())
for f in report.findings:
    print(f.code.value, f.severity.value, f.rationale)
```

## How it works

1. **Segment** (`segment.py`) — split text at numbered headings (`1.`, `1.1`,
   `2)`), `ARTICLE`/`Section` markers, lettered sub-points and standalone
   heading lines. Crash-proof on arbitrary input (property-tested).
2. **Classify** (`classify.py` + `cues.py`) — score each clause against every
   clause type by summing weighted cue matches (headings weighted higher);
   argmax wins above a threshold, else `OTHER`.
3. **Flag risk** (`risk.py`) — rules over typed clauses with negation and
   scope handling (a capped liability clause is not flagged; a bilateral
   termination-for-convenience is not flagged; a definitions clause mentioning
   "liabilities" raises no liability risk).
4. **Benchmark** (`generate.py`, `baselines.py`, `metrics.py`, `bench.py`) —
   seeded synthetic contracts with known labels, scored against baselines.

## Layout

```
src/clausewise/
  __init__.py      public API (analyze, models)
  py.typed         PEP 561 marker
  models.py        pydantic v2 models: Clause, RiskFinding, Report, enums
  segment.py       clause segmentation
  cues.py          cue lexicons and weights (the "knowledge")
  classify.py      weighted cue-score classifier
  risk.py          risk rules (present + missing)
  analyze.py       text -> Report pipeline
  generate.py      seeded synthetic contract generator with gold labels
  baselines.py     ours / keyword-only / random detectors
  metrics.py       P/R/F1, bootstrap CI, paired permutation test
  bench.py         benchmark harness + results/manifest writers
  cli.py           argparse CLI: `bench`, `review`
tests/             88 tests (pytest + Hypothesis)
benchmarks/        results.json, manifest.json (written by `bench`)
docs/adr/          architecture decision records
```

## Reproducing the numbers

```bash
clausewise bench
cat benchmarks/results.json
cat benchmarks/manifest.json   # git sha (or "n/a"), python version, dataset checksum
```

The manifest records the dataset checksum (a SHA-256 over every contract's text
and gold labels) so a changed corpus is detectable. The git SHA falls back to
`"n/a"` when the code is not run from a git checkout.

## Known gaps

* **Non-standard phrasing is missed.** Cue-based classification and flagging
  only catch the wordings in `cues.py` and `risk.py`. A clause that conveys a
  risk in unusual language (a renewal with no renewal word, a one-sided
  termination that never says "for convenience") is under-detected; a real cap
  or governing-law clause phrased oddly can be mislabelled. The Results error
  table quantifies both directions.
* **English only, and US-style commercial contracts.** The lexicons assume
  English and common US drafting conventions.
* **Synthetic evaluation.** The benchmark measures performance on generated
  contracts, deliberately made hard and kept independent of the detector
  (ADR 0002), but it is not a substitute for a labelled corpus of real
  contracts, which this project does not ship.
* **Set-level findings.** At most one finding per risk code per contract is
  reported; the tool does not enumerate every clause that triggers a code.
* **Severity is fixed per risk code**, not inferred from the specific wording.
* **No clause rewriting or remediation** — clausewise flags; it does not draft
  fixes.

## Development

```bash
.venv/bin/ruff check .
.venv/bin/pytest -q
```

CI runs ruff, the test suite and a benchmark smoke run on Python 3.10, 3.11 and
3.12 (`.github/workflows/ci.yml`).

## License

MIT — see [LICENSE](LICENSE).
