"""Check for lockfiles + toolchain pins."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


LOCKFILES = {
    "Cargo.lock": "Rust",
    "package-lock.json": "npm",
    "yarn.lock": "Yarn",
    "pnpm-lock.yaml": "pnpm",
    "poetry.lock": "Poetry",
    "uv.lock": "uv",
    "Pipfile.lock": "Pipenv",
}

TOOLCHAIN_PINS = {
    "rust-toolchain.toml": "Rust",
    ".tool-versions": "asdf",
    ".nvmrc": "Node",
    ".python-version": "Python",
}


@dataclass
class ReproducibilityResult:
    score: int
    lockfiles: list[str] = field(default_factory=list)
    toolchain_pins: list[str] = field(default_factory=list)
    notes: str = ""


def detect(path: Path) -> ReproducibilityResult:
    lf: list[str] = []
    for name, ecosystem in LOCKFILES.items():
        if (path / name).is_file():
            lf.append(f"{name} ({ecosystem})")

    tc: list[str] = []
    for name, ecosystem in TOOLCHAIN_PINS.items():
        if (path / name).is_file():
            tc.append(f"{name} ({ecosystem})")

    if not lf and not tc:
        return ReproducibilityResult(score=0, notes="no lockfiles or toolchain pins found")

    score = 0
    if lf:
        score += 6
    if tc:
        score += 4
    score = min(10, score)

    parts = []
    if lf:
        parts.append(f"lockfile(s): {len(lf)}")
    if tc:
        parts.append(f"pin(s): {len(tc)}")

    return ReproducibilityResult(score=score, lockfiles=lf, toolchain_pins=tc, notes=", ".join(parts))
