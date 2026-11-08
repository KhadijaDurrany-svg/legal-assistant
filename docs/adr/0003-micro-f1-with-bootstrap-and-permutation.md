# 3. Micro-F1 headline, bootstrap CI, paired permutation p-value

Status: accepted

## Context

Each contract produces a *set* of risk findings. We need (a) a single headline
quality number, (b) an honest uncertainty interval on it, and (c) a defensible
statement that our detector beats a baseline rather than being lucky on one
corpus.

## Decision

* **Headline:** micro-averaged precision/recall/F1 over every
  `(contract, risk_code)` pair in the corpus. Micro-averaging weights every
  finding equally and is not distorted by contracts that happen to have few
  findings.
* **Uncertainty:** a contract-level percentile bootstrap (default 2000
  resamples) gives a 95% CI on micro-F1. Resampling whole contracts, not
  individual findings, respects the fact that findings within one contract are
  correlated.
* **Significance:** a two-sided paired permutation test on *per-contract* F1
  (default 10000 permutations, add-one smoothed p-value). It is paired because
  both detectors see the same contracts, and permutation because it assumes no
  distribution on the scores — under the null the two systems' per-contract
  scores are exchangeable, so each permutation flips a random subset of signs.

A contract with no gold and no predicted findings scores per-contract F1 = 1.0:
staying silent on a clean contract is correct behaviour and should count as
such.

## Consequences

* The README reports CIs alongside every F1 and a p-value for each baseline
  comparison, all from a real run (`benchmarks/results.json`).
* With the default corpus the CIs for the three detectors do not overlap and
  both permutation p-values hit the resolution floor (`1 / (n_perm + 1)`),
  i.e. no permutation reached the observed gap. That floor is reported honestly
  as `0.0001` rather than rounded to `0`.
* Per-contract F1 is a slightly different quantity from micro-F1; we report the
  mean per-contract F1 delta next to the micro-F1 delta so the significance
  test and the headline are not conflated.
