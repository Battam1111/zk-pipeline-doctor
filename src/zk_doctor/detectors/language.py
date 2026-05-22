"""Detect which ZK language(s) and proving systems are used in a project."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


# File-extension -> human-readable ZK language label
EXT_MAP = {
    ".compact": "Compact (Midnight)",
    ".leo": "Leo (Aleo)",
    ".aleo": "Aleo bytecode",
    ".nr": "Noir",
    ".cairo": "Cairo (Starknet)",
}

# Rust-based zkVMs/proving systems are detected via Cargo.toml dependency scanning.
# Each entry: (label, [substring patterns]) — if any pattern matches the Cargo.toml,
# the label is counted as a detected ZK ecosystem.
RUST_ZK_DEPS = [
    ("Rust + risc0",          ["risc0-zkvm", "risc0-build", "risc0_zkvm"]),
    ("Rust + SP1 (Succinct)", ["sp1-zkvm", "sp1-build", "sp1_sdk", "sp1_zkvm"]),
    ("Rust + Plonky3",        ["p3-air", "p3-field", "p3-uni-stark", "p3-matrix", "plonky3"]),
    ("Rust + Stwo",           ["stwo-prover", "stwo-cairo", "stwo_prover"]),
    ("Rust + OpenVM",         ["openvm-circuit", "openvm-stark-backend", "openvm-sdk"]),
    ("Rust + Nexus zkVM",     ["nexus-zkvm", "nexus_zkvm", "nexus-prover"]),
    ("Rust + Jolt",           ["jolt-core", "jolt-sdk"]),
]

# Cairo M is a Cairo dialect; detect by Scarb.toml entries or attribute usage
CAIRO_M_DEPS = ["cairo_m", "cairo-m", "kkrt-labs/cairo-m"]

# Solidity verifier patterns: .sol files that look like ZK pairing verifiers
SOL_VERIFIER_PATTERNS = [
    r"\bpairing\b",
    r"BN254|bn254",
    r"BLS12_?381|bls12.?381",
    r"function verify(?:Proof)?\b",
    r"@openzeppelin/contracts/utils/cryptography",
]

_SKIP_DIRS = {"node_modules", "target", "dist", "build", ".venv", "__pycache__", "vendor"}


@dataclass
class LanguageResult:
    score: int
    languages: dict[str, int] = field(default_factory=dict)
    notes: str = ""


def _scan_cargo(path: Path) -> str:
    """Concatenate all Cargo.toml content recursively, lowercased."""
    chunks: list[str] = []
    for cargo in path.rglob("Cargo.toml"):
        if any(p in _SKIP_DIRS for p in cargo.parts):
            continue
        try:
            chunks.append(cargo.read_text(errors="ignore"))
        except Exception:
            pass
    return "\n".join(chunks).lower()


def _scan_scarb(path: Path) -> str:
    """Concatenate all Scarb.toml content."""
    chunks: list[str] = []
    for s in path.rglob("Scarb.toml"):
        if any(p in _SKIP_DIRS for p in s.parts):
            continue
        try:
            chunks.append(s.read_text(errors="ignore"))
        except Exception:
            pass
    return "\n".join(chunks).lower()


def _detect_solidity_verifiers(path: Path) -> tuple[int, list[str]]:
    """Return (count, list of verifier file paths) for .sol files matching ZK verifier heuristics."""
    found: list[str] = []
    for f in path.rglob("*.sol"):
        if any(p in _SKIP_DIRS for p in f.parts):
            continue
        try:
            text = f.read_text(errors="ignore")
        except Exception:
            continue
        has_pairing = bool(re.search(SOL_VERIFIER_PATTERNS[0], text, re.IGNORECASE))
        has_curve = bool(re.search(SOL_VERIFIER_PATTERNS[1], text)) or bool(re.search(SOL_VERIFIER_PATTERNS[2], text))
        has_verify_fn = bool(re.search(SOL_VERIFIER_PATTERNS[3], text))
        # Strong signal: pairing precompile + (curve OR verify function); OR curve + verify-fn together
        if (has_pairing and (has_curve or has_verify_fn)) or (has_curve and has_verify_fn):
            found.append(str(f.relative_to(path)))
    return len(found), found[:5]


def _has_cairo_m_attribute(path: Path) -> bool:
    """Check any .cairo file for #[cairo_m] attribute usage."""
    for f in path.rglob("*.cairo"):
        if any(p in _SKIP_DIRS for p in f.parts):
            continue
        try:
            if "#[cairo_m]" in f.read_text(errors="ignore"):
                return True
        except Exception:
            continue
    return False


def detect(path: Path) -> LanguageResult:
    """Walk the path looking for ZK source files + Rust-based zkVM deps + Solidity verifiers."""
    if not path.exists():
        return LanguageResult(score=0, notes="path does not exist")

    counts: dict[str, int] = {}

    # === file-extension scan ===
    for f in path.rglob("*"):
        if not f.is_file():
            continue
        if any(part in _SKIP_DIRS for part in f.parts):
            continue
        lang = EXT_MAP.get(f.suffix)
        if lang:
            counts[lang] = counts.get(lang, 0) + 1

    # === Rust-based zkVM scan ===
    cargo_text = _scan_cargo(path)
    if cargo_text:
        for label, patterns in RUST_ZK_DEPS:
            if any(pat.lower() in cargo_text for pat in patterns):
                count = sum(cargo_text.count(pat.lower()) for pat in patterns)
                counts[label] = max(1, count)

    # === Cairo M sub-detection (only meaningful if Cairo files / Scarb.toml exist) ===
    has_cairo = "Cairo (Starknet)" in counts
    scarb_text = _scan_scarb(path)
    if has_cairo or scarb_text:
        if (scarb_text and any(p in scarb_text for p in CAIRO_M_DEPS)) or _has_cairo_m_attribute(path):
            counts["Cairo M (kkrt-labs)"] = counts.get("Cairo M (kkrt-labs)", 0) + 1

    # === Solidity verifier scan ===
    sol_count, sol_files = _detect_solidity_verifiers(path)
    if sol_count > 0:
        counts["Solidity ZK verifier"] = sol_count

    if not counts:
        return LanguageResult(
            score=0,
            notes="no ZK source files / Rust zkVM deps / Solidity verifiers found",
        )

    top = sorted(counts.items(), key=lambda x: -x[1])
    note_parts = [f"{lang}: {n} file(s)" for lang, n in top]
    if sol_files:
        note_parts.append("example verifier files: " + ", ".join(sol_files[:3]))
    notes = ", ".join(note_parts)
    return LanguageResult(score=10, languages=counts, notes=notes)
