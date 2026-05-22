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

def test_language_risc0_via_cargo():
    """Existing risc0 fallback should still work via Cargo.toml."""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "Cargo.toml").write_text("""[dependencies]
risc0-zkvm = "1.0"
""")
        r = language.detect(Path(d))
        assert r.score == 10
        assert "Rust + risc0" in r.languages


def test_language_sp1_via_cargo():
    """SP1 detected via Cargo.toml sp1-zkvm dep."""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "Cargo.toml").write_text("""[dependencies]
sp1-zkvm = "3.0"
sp1-build = "3.0"
""")
        r = language.detect(Path(d))
        assert r.score == 10
        assert "Rust + SP1 (Succinct)" in r.languages


def test_language_plonky3_via_cargo():
    """Plonky3 detected via p3-* dep family."""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "Cargo.toml").write_text("""[dependencies]
p3-air = "0.1"
p3-field = "0.1"
p3-uni-stark = "0.1"
""")
        r = language.detect(Path(d))
        assert r.score == 10
        assert "Rust + Plonky3" in r.languages


def test_language_stwo_via_cargo():
    """Stwo detected via stwo-prover dep."""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "Cargo.toml").write_text("""[dependencies]
stwo-prover = { git = "https://github.com/starkware-libs/stwo" }
""")
        r = language.detect(Path(d))
        assert r.score == 10
        assert "Rust + Stwo" in r.languages


def test_language_solidity_verifier():
    """A .sol file with pairing + verify function is detected."""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "Verifier.sol").write_text("""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

library Pairing {
    function pairing(G1Point[] memory p1, G2Point[] memory p2) internal view returns (bool) {
        // ... BN254 pairing precompile call
    }
}

contract Verifier {
    function verifyProof(uint[2] memory a, uint[2][2] memory b, uint[2] memory c, uint[1] memory input) public view returns (bool) {
        // ...
    }
}
""")
        r = language.detect(Path(d))
        assert r.score == 10
        assert "Solidity ZK verifier" in r.languages


def test_language_cairo_m_via_scarb():
    """Cairo M detected via Scarb.toml + .cairo file."""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "main.cairo").write_text("fn main() {}")
        (Path(d) / "Scarb.toml").write_text("""[package]
name = "myproject"

[dependencies]
cairo_m = "0.1"
""")
        r = language.detect(Path(d))
        assert r.score == 10
        assert "Cairo M (kkrt-labs)" in r.languages


def test_language_no_false_positive_on_normal_rust():
    """A plain Rust project with no ZK deps should not be flagged."""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "Cargo.toml").write_text("""[dependencies]
serde = "1.0"
tokio = "1.40"
""")
        r = language.detect(Path(d))
        # No ZK files, no ZK deps → score 0
        assert r.score == 0


def test_language_no_false_positive_on_normal_sol():
    """A plain ERC20 contract should NOT be flagged as ZK verifier."""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "Token.sol").write_text("""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MyToken is ERC20 {
    constructor() ERC20("My", "MY") {
        _mint(msg.sender, 1000 ether);
    }
}
""")
        r = language.detect(Path(d))
        assert "Solidity ZK verifier" not in r.languages
