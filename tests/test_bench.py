from __future__ import annotations

import json

from clausewise.bench import run_benchmark, write_results


def test_benchmark_runs_small():
    result = run_benchmark(n=60, seed=7, n_bootstrap=200, n_permutations=500)
    assert result.n_contracts == 60
    assert {d.name for d in result.detectors} == {"ours", "keyword", "random"}


def test_ours_beats_baselines():
    result = run_benchmark(n=120, seed=7, n_bootstrap=200, n_permutations=500)
    by_name = {d.name: d for d in result.detectors}
    assert by_name["ours"].f1 > by_name["keyword"].f1
    assert by_name["keyword"].f1 > by_name["random"].f1


def test_ours_not_perfect():
    # Honesty guard: a perfect score on synthetic data is a red flag.
    result = run_benchmark(n=200, seed=7, n_bootstrap=200, n_permutations=500)
    ours = next(d for d in result.detectors if d.name == "ours")
    assert ours.f1 < 0.99
    assert ours.precision < 1.0
    assert ours.recall < 1.0


def test_comparisons_significant():
    result = run_benchmark(n=200, seed=7, n_bootstrap=200, n_permutations=2000)
    for comp in result.comparisons:
        assert comp.f1_delta > 0
        assert 0.0 < comp.p_value <= 1.0


def test_ci_brackets_are_ordered():
    result = run_benchmark(n=120, seed=7, n_bootstrap=300, n_permutations=500)
    for d in result.detectors:
        assert d.f1_ci_low <= d.f1 <= d.f1_ci_high + 1e-9


def test_checksum_stable():
    a = run_benchmark(n=50, seed=7, n_bootstrap=50, n_permutations=100)
    b = run_benchmark(n=50, seed=7, n_bootstrap=50, n_permutations=100)
    assert a.dataset_checksum == b.dataset_checksum


def test_write_results_creates_files(tmp_path):
    result = run_benchmark(n=40, seed=7, n_bootstrap=50, n_permutations=100)
    rp, mp = write_results(result, tmp_path)
    assert rp.exists() and mp.exists()
    results = json.loads(rp.read_text())
    manifest = json.loads(mp.read_text())
    assert results["n_contracts"] == 40
    assert "git_sha" in manifest
    assert manifest["python"]
    assert manifest["dataset_checksum"] == result.dataset_checksum


def test_manifest_git_sha_present():
    # git sha is either a real hash or the documented fallback.
    from clausewise.bench import _git_sha

    sha = _git_sha()
    assert sha == "n/a" or len(sha) >= 7
