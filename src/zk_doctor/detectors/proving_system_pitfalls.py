"""Pro detector: cross-ecosystem proving-system pitfalls.

Looks for known footguns by ecosystem:
  - risc0  : RISC0_DEV_MODE leaked into release builds; missing receipt verify
             on host side; build using `prove_with_opts` without `dev: false`
  - SP1    : patched-deps section missing for crypto primitives (sha2, k256,
             ed25519, tiny-keccak — Succinct's known accelerated patches)
  - Plonky3: PCS / config trivially defaulted; missing `BabyBear`/`Goldilocks`
             field choice in trace generation; AIR width hard-coded as 1
  - Stwo   : default blowup-factor on a non-toy circuit; missing
             `StarkProofConfig::new` customization
  - Compact: `circuit foo()` declared but no companion .compact tests
  - Noir   : `nargo.toml` missing `[package]` section or compiler version pin

The point isn't to be perfectly accurate; it's to give pros a checklist of
"things I should think about" that's hard to bake into the free tier without
a lot of code. This file is the pro-tier equivalent of `security.py` but for
proving-system soundness instead of git hygiene.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from zk_doctor.pro import pro_only


_SKIP_DIRS = {"node_modules", "target", "dist", "build", ".venv", "__pycache__", "vendor", ".git"}


@dataclass
class PitfallsResult:
    score: int
    findings: list[str] = field(default_factory=list)
    notes: str = ""


def _walk(path: Path, glob: str):
    for f in path.rglob(glob):
        if not f.is_file():
            continue
        if any(part in _SKIP_DIRS for part in f.parts):
            continue
        yield f


def _safe_text(p: Path) -> str:
    try:
        return p.read_text(errors="ignore")
    except Exception:
        return ""


def _scan_cargo(path: Path) -> tuple[str, list[Path]]:
    """Return (concatenated_lowercased_text, list_of_files)."""
    chunks: list[str] = []
    files: list[Path] = []
    for cargo in path.rglob("Cargo.toml"):
        if any(p in _SKIP_DIRS for p in cargo.parts):
            continue
        files.append(cargo)
        chunks.append(_safe_text(cargo))
    return "\n".join(chunks).lower(), files


@pro_only(
    name="proving_system_pitfalls",
    summary="Cross-ecosystem soundness footguns: risc0 dev-mode leak, SP1 missing patches, Plonky3 default PCS config, Stwo default blowup, Noir/Compact toolchain pins.",
)
def detect(path: Path) -> PitfallsResult:
    findings: list[str] = []
    cargo_text, _ = _scan_cargo(path)

    # ---- risc0 ----
    if "risc0-zkvm" in cargo_text or "risc0_zkvm" in cargo_text:
        # Look for dev-mode leaks
        for f in _walk(path, "*.rs"):
            t = _safe_text(f)
            if re.search(r"RISC0_DEV_MODE\s*=\s*[\"']?1", t) or "dev_mode: true" in t:
                findings.append(
                    f"risc0 dev mode appears enabled in {f.relative_to(path)} — "
                    "RISC0_DEV_MODE=1 skips proof generation and must NOT ship"
                )
        # Look for missing receipt verify on the host
        host_has_verify = False
        for f in _walk(path, "*.rs"):
            t = _safe_text(f)
            if ".verify(" in t and ("receipt" in t.lower() or "Receipt" in t):
                host_has_verify = True
                break
        if not host_has_verify:
            findings.append(
                "risc0 host code: no `Receipt::verify(...)` call found — verify "
                "you're actually checking proofs in the host program"
            )

    # ---- SP1 ----
    if "sp1-zkvm" in cargo_text or "sp1_zkvm" in cargo_text:
        # SP1 ships precompiled curves & hashes via `[patch.crates-io]` — many
        # projects miss the patches and run the unpatched code, losing 10-100x
        # performance + sometimes correctness in edge cases.
        if "[patch.crates-io]" not in cargo_text:
            findings.append(
                "SP1 project: no `[patch.crates-io]` section in any Cargo.toml — "
                "you'll miss Succinct's accelerated sha2 / k256 / ed25519 / tiny-keccak patches"
            )

    # ---- Plonky3 ----
    if "p3-air" in cargo_text or "p3-field" in cargo_text:
        # Default PCS / field
        any_field_pinned = False
        for f in _walk(path, "*.rs"):
            t = _safe_text(f)
            if "BabyBear" in t or "Goldilocks" in t or "Mersenne31" in t or "KoalaBear" in t:
                any_field_pinned = True
                break
        if not any_field_pinned:
            findings.append(
                "Plonky3: no explicit field type found in source (BabyBear / Goldilocks / Mersenne31 / KoalaBear) — "
                "double-check you're not relying on a default-generic that may not be sound for your trace"
            )
        # AIR width hard-coded as 1 is a copy-paste tutorial smell
        for f in _walk(path, "*.rs"):
            t = _safe_text(f)
            if re.search(r"TRACE_WIDTH\s*[:=]\s*1\b", t):
                findings.append(
                    f"Plonky3: TRACE_WIDTH=1 in {f.relative_to(path)} — likely "
                    "a tutorial leftover; real AIRs almost always need wider traces"
                )
                break

    # ---- Stwo ----
    if "stwo-prover" in cargo_text or "stwo_prover" in cargo_text:
        # Missing StarkProofConfig customization is a smell
        any_config = False
        for f in _walk(path, "*.rs"):
            t = _safe_text(f)
            if "StarkProofConfig" in t or "ProofConfig" in t:
                any_config = True
                break
        if not any_config:
            findings.append(
                "Stwo: no StarkProofConfig customization found — proving with "
                "library defaults may be too conservative for production"
            )

    # ---- Compact (Midnight) ----
    has_compact = any(_walk(path, "*.compact"))
    if has_compact:
        # Compact .compact files with circuits but no test directory
        circuit_count = 0
        for f in _walk(path, "*.compact"):
            circuit_count += len(re.findall(r"^\s*circuit\s+\w+", _safe_text(f), re.MULTILINE))
        if circuit_count >= 2 and not (path / "tests").is_dir() and not (path / "test").is_dir():
            findings.append(
                f"Compact: {circuit_count} circuits across .compact files but no "
                "tests/ directory — circuit logic without tests is high risk"
            )

    # ---- Noir ----
    has_nargo = (path / "Nargo.toml").is_file() or any(path.rglob("Nargo.toml"))
    if has_nargo:
        for nargo in [path / "Nargo.toml", *path.rglob("Nargo.toml")]:
            if not nargo.is_file():
                continue
            if any(p in _SKIP_DIRS for p in nargo.parts):
                continue
            t = _safe_text(nargo)
            if "[package]" not in t:
                findings.append(
                    f"Noir {nargo.relative_to(path)}: missing [package] section "
                    "— manifest may not be valid"
                )
            if "compiler_version" not in t:
                findings.append(
                    f"Noir {nargo.relative_to(path)}: no compiler_version pin — "
                    "rebuilds may silently shift across toolchains"
                )

    if not findings:
        return PitfallsResult(score=10, notes="no known proving-system footguns detected")

    score = max(0, 10 - len(findings) * 2)
    return PitfallsResult(score=score, findings=findings, notes=f"{len(findings)} pitfall(s) flagged")
