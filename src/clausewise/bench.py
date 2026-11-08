"""Benchmark harness: run every detector over a seeded synthetic corpus.

Produces a results object with micro precision/recall/F1 per detector,
bootstrap 95% CIs on F1, and paired permutation p-values for ours vs each
baseline. All numbers come from a real run; nothing is hard-coded.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from .baselines import RandomDetector, detect_ours, keyword_detector
from .generate import generate_corpus
from .metrics import (
    bootstrap_f1_ci,
    micro_prf,
    paired_permutation_pvalue,
)
from .models import RiskCode


@dataclass
class DetectorResult:
    name: str
    precision: float
    recall: float
    f1: float
    f1_ci_low: float
    f1_ci_high: float
    tp: int
    fp: int
    fn: int


@dataclass
class Comparison:
    baseline: str
    f1_delta: float
    mean_per_contract_f1_delta: float
    p_value: float


@dataclass
class BenchResult:
    n_contracts: int
    seed: int
    n_bootstrap: int
    n_permutations: int
    detectors: list[DetectorResult]
    comparisons: list[Comparison]
    dataset_checksum: str


def _checksum(texts: list[str], golds: list[frozenset[RiskCode]]) -> str:
    h = hashlib.sha256()
    for text, gold in zip(texts, golds, strict=True):
        h.update(text.encode("utf-8"))
        h.update(b"\x00")
        h.update(",".join(sorted(c.value for c in gold)).encode("utf-8"))
        h.update(b"\x01")
    return h.hexdigest()


def run_benchmark(
    n: int = 400,
    seed: int = 7,
    n_bootstrap: int = 2000,
    n_permutations: int = 10000,
) -> BenchResult:
    """Run the full benchmark and return the measured results."""
    corpus = generate_corpus(n, seed)
    texts = [c.text for c in corpus]
    golds = [c.gold for c in corpus]
    gold_sets: list[set[RiskCode]] = [set(g) for g in golds]

    rnd = RandomDetector(seed=seed + 1)
    detectors = {
        "ours": [detect_ours(t) for t in texts],
        "keyword": [keyword_detector(t) for t in texts],
        "random": [rnd(t) for t in texts],
    }

    results: list[DetectorResult] = []
    for name, preds in detectors.items():
        prf = micro_prf(preds, gold_sets)
        lo, hi = bootstrap_f1_ci(preds, gold_sets, n_boot=n_bootstrap, seed=seed + 2)
        results.append(
            DetectorResult(
                name=name,
                precision=round(prf.precision, 4),
                recall=round(prf.recall, 4),
                f1=round(prf.f1, 4),
                f1_ci_low=round(lo, 4),
                f1_ci_high=round(hi, 4),
                tp=prf.tp,
                fp=prf.fp,
                fn=prf.fn,
            )
        )

    ours_f1 = micro_prf(detectors["ours"], gold_sets).f1
    comparisons: list[Comparison] = []
    for base in ("keyword", "random"):
        base_f1 = micro_prf(detectors[base], gold_sets).f1
        obs, p = paired_permutation_pvalue(
            detectors["ours"], detectors[base], gold_sets, n_perm=n_permutations, seed=seed + 3
        )
        comparisons.append(
            Comparison(
                baseline=base,
                f1_delta=round(ours_f1 - base_f1, 4),
                mean_per_contract_f1_delta=round(obs, 4),
                p_value=round(p, 6),
            )
        )

    return BenchResult(
        n_contracts=n,
        seed=seed,
        n_bootstrap=n_bootstrap,
        n_permutations=n_permutations,
        detectors=results,
        comparisons=comparisons,
        dataset_checksum=_checksum(texts, golds),
    )


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "n/a"


def write_results(result: BenchResult, out_dir: Path) -> tuple[Path, Path]:
    """Write ``results.json`` and ``manifest.json`` into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.json"
    manifest_path = out_dir / "manifest.json"
    results_path.write_text(json.dumps(asdict(result), indent=2, sort_keys=True) + "\n")
    manifest = {
        "git_sha": _git_sha(),
        "python": platform.python_version(),
        "dataset_checksum": result.dataset_checksum,
        "n_contracts": result.n_contracts,
        "seed": result.seed,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return results_path, manifest_path
