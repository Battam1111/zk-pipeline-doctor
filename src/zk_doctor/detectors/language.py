"""Detect which ZK language(s) are used in a project."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


EXT_MAP = {
    ".compact": "Compact (Midnight)",
    ".leo": "Leo (Aleo)",
    ".aleo": "Aleo bytecode",
    ".nr": "Noir",
    ".cairo": "Cairo (Starknet)",
}


@dataclass
class LanguageResult:
    score: int
    languages: dict[str, int] = field(default_factory=dict)
    notes: str = ""


def detect(path: Path) -> LanguageResult:
    """Walk the path looking for ZK source files. Returns a LanguageResult."""
    if not path.exists():
        return LanguageResult(score=0, notes="path does not exist")

    counts: dict[str, int] = {}
    skip_dirs = {"node_modules", "target", "dist", "build", ".venv", "__pycache__"}

    for f in path.rglob("*"):
        if not f.is_file():
            continue
        if any(part in skip_dirs for part in f.parts):
            continue
        lang = EXT_MAP.get(f.suffix)
        if lang:
            counts[lang] = counts.get(lang, 0) + 1

    # Fallback: Rust+risc0 detection via Cargo.toml
    if not counts:
        cargo = path / "Cargo.toml"
        if cargo.exists() and "risc0" in cargo.read_text(errors="ignore").lower():
            counts["Rust + risc0"] = 1

    if not counts:
        return LanguageResult(score=0, notes="no ZK source files found")

    top = sorted(counts.items(), key=lambda x: -x[1])
    notes = ", ".join(f"{lang}: {n} file(s)" for lang, n in top)
    return LanguageResult(score=10, languages=counts, notes=notes)
