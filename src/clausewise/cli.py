"""Command-line interface for clausewise.

Subcommands
-----------
``bench``   run the benchmark; prints a table and (by default) writes
            ``benchmarks/results.json`` and ``benchmarks/manifest.json``.
``review``  analyze a contract text file and print its clauses and risk flags.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyze import analyze
from .bench import run_benchmark, write_results


def _cmd_bench(args: argparse.Namespace) -> int:
    result = run_benchmark(
        n=args.n,
        seed=args.seed,
        n_bootstrap=args.bootstrap,
        n_permutations=args.permutations,
    )
    print(f"corpus: {result.n_contracts} contracts  seed={result.seed}")
    print(f"{'detector':<10}{'prec':>8}{'rec':>8}{'f1':>8}   {'f1 95% CI':>18}")
    for d in result.detectors:
        ci = f"[{d.f1_ci_low:.3f}, {d.f1_ci_high:.3f}]"
        print(f"{d.name:<10}{d.precision:>8.3f}{d.recall:>8.3f}{d.f1:>8.3f}   {ci:>18}")
    print()
    for c in result.comparisons:
        print(
            f"ours vs {c.baseline:<8} F1 delta={c.f1_delta:+.3f}  "
            f"mean per-contract F1 delta={c.mean_per_contract_f1_delta:+.3f}  "
            f"p={c.p_value:.4g}"
        )
    if not args.no_write:
        out_dir = Path(args.out)
        rp, mp = write_results(result, out_dir)
        print(f"\nwrote {rp}\nwrote {mp}")
    return 0


def _cmd_review(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f"error: no such file: {path}", file=sys.stderr)
        return 2
    report = analyze(path.read_text(encoding="utf-8", errors="replace"))
    print(f"{len(report.clauses)} clause(s):")
    for c in report.clauses:
        head = c.heading or "(preamble)"
        print(f"  [{c.index}] {head}  ->  {c.clause_type.value} (score {c.type_score:.1f})")
    if report.findings:
        print(f"\n{len(report.findings)} risk finding(s):")
        for f in sorted(report.findings, key=lambda x: x.code.value):
            where = f"clause {f.clause_index}" if f.clause_index is not None else "document"
            print(f"  [{f.severity.value:>6}] {f.code.value:<24} ({where}): {f.rationale}")
    else:
        print("\nno risk findings")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clausewise",
        description="Offline contract clause extractor and risk flagger.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("bench", help="run the detection benchmark")
    b.add_argument("--n", type=int, default=400, help="number of synthetic contracts")
    b.add_argument("--seed", type=int, default=7, help="random seed")
    b.add_argument("--bootstrap", type=int, default=2000, help="bootstrap resamples")
    b.add_argument("--permutations", type=int, default=10000, help="permutation iterations")
    b.add_argument("--out", default="benchmarks", help="output directory")
    b.add_argument("--no-write", action="store_true", help="do not write result files")
    b.set_defaults(func=_cmd_bench)

    r = sub.add_parser("review", help="flag risks in a contract text file")
    r.add_argument("file", help="path to a contract .txt file")
    r.set_defaults(func=_cmd_review)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
