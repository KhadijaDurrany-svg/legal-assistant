from __future__ import annotations

import json

from clausewise.cli import main


def test_review_command(tmp_path, capsys):
    contract = tmp_path / "c.txt"
    contract.write_text(
        "1. Termination\nThe Company may terminate at any time for convenience.\n"
        "2. Liability\nUnlimited liability for all damages.\n"
    )
    rc = main(["review", str(contract)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "clause" in out.lower()
    assert "uncapped_liability" in out
    assert "unilateral_termination" in out


def test_review_missing_file(capsys):
    rc = main(["review", "/no/such/file.txt"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "no such file" in err


def test_review_no_findings(tmp_path, capsys):
    contract = tmp_path / "safe.txt"
    contract.write_text(
        "1. Termination\nEither party may terminate for cause.\n"
        "2. Governing Law\nGoverned by Delaware law.\n"
        "3. Confidentiality\nKeep it confidential.\n"
        "4. Liability\nAggregate liability shall not exceed fees paid.\n"
    )
    rc = main(["review", str(contract)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "no risk findings" in out


def test_bench_no_write(capsys):
    rc = main(["bench", "--n", "40", "--bootstrap", "50", "--permutations", "100", "--no-write"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ours" in out
    assert "keyword" in out
    assert "wrote" not in out


def test_bench_writes(tmp_path, capsys):
    out_dir = tmp_path / "bench_out"
    rc = main(
        [
            "bench",
            "--n",
            "40",
            "--bootstrap",
            "50",
            "--permutations",
            "100",
            "--out",
            str(out_dir),
        ]
    )
    capsys.readouterr()
    assert rc == 0
    results = json.loads((out_dir / "results.json").read_text())
    assert results["n_contracts"] == 40
    assert (out_dir / "manifest.json").exists()
