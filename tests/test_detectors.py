"""Smoke tests for the 6 detectors."""

from __future__ import annotations

import tempfile
from pathlib import Path

from zk_doctor.detectors import ci, docs, language, reproducibility, security, tests as t_det


def test_language_empty():
    with tempfile.TemporaryDirectory() as d:
        r = language.detect(Path(d))
        assert r.score == 0


def test_language_compact():
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "hello.compact").write_text("circuit Hello { }")
        r = language.detect(Path(d))
        assert r.score == 10
        assert "Compact (Midnight)" in r.languages


def test_language_noir():
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "main.nr").write_text("fn main() {}")
        r = language.detect(Path(d))
        assert r.score == 10
        assert "Noir" in r.languages


def test_tests_no_tests():
    with tempfile.TemporaryDirectory() as d:
        r = t_det.detect(Path(d))
        assert r.score == 0


def test_tests_with_dir():
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "tests").mkdir()
        (Path(d) / "tests" / "test_basic.py").write_text("def test_x(): pass")
        r = t_det.detect(Path(d))
        assert r.score >= 4


def test_ci_no_workflows():
    with tempfile.TemporaryDirectory() as d:
        r = ci.detect(Path(d))
        assert r.score == 0


def test_ci_with_workflow():
    with tempfile.TemporaryDirectory() as d:
        wf = Path(d) / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "test.yml").write_text("name: test\n")
        r = ci.detect(Path(d))
        assert r.score >= 6


def test_docs_no_readme():
    with tempfile.TemporaryDirectory() as d:
        r = docs.detect(Path(d))
        assert r.score == 0


def test_docs_with_readme():
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "README.md").write_text("# Project\n\n" + "word " * 300)
        r = docs.detect(Path(d))
        assert r.score >= 5


def test_security_clean():
    with tempfile.TemporaryDirectory() as d:
        gi = Path(d) / ".gitignore"
        gi.write_text("node_modules\ntarget\ndist\nbuild\n.env\n*.key\n*.pem\n")
        r = security.detect(Path(d))
        assert r.score == 10


def test_security_no_gitignore():
    with tempfile.TemporaryDirectory() as d:
        r = security.detect(Path(d))
        # Missing .gitignore = at least one finding
        assert r.score < 10


def test_reproducibility_empty():
    with tempfile.TemporaryDirectory() as d:
        r = reproducibility.detect(Path(d))
        assert r.score == 0


def test_reproducibility_with_lockfile():
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "Cargo.lock").write_text("[[package]]\nname = \"x\"\n")
        r = reproducibility.detect(Path(d))
        assert r.score >= 6
