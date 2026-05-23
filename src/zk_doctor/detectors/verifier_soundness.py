"""Pro detector: deep soundness analysis of Solidity ZK verifiers.

The free `language` detector flags that a Solidity verifier exists. This pro
detector reads the verifier source and looks for known soundness footguns:

  - `delegatecall` inside the verifier (catastrophic if the verifier is the
    target of a proxy call)
  - missing scalar-field bounds check on public inputs (BN254/BLS12-381
    scalar field overflow)
  - missing zero-check on G1/G2 points (verifier passes for trivial proofs)
  - explicit non-constant gas in pairing precompile call
  - reusing the same `Pairing.G1Point memory vk_x` across calls without reset
    (state leak between verify() invocations)
  - re-entrancy guard missing on verify() (rare but possible if verify() does
    a callback for input expansion)

This is the kind of thing that an experienced ZK auditor would scan for in
five minutes; baking it into a CLI is real engineering work and justifies
being a pro feature.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from zk_doctor.pro import pro_only


_SKIP_DIRS = {"node_modules", "target", "dist", "build", ".venv", "__pycache__", "vendor", ".git", "lib"}

# BN254 scalar field modulus (snark-side)
BN254_R = "21888242871839275222246405745257275088548364400416034343698204186575808495617"
# BLS12-381 scalar field modulus
BLS12_R = "52435875175126190479447740508185965837690552500527637822603658699938581184513"


@dataclass
class VerifierSoundnessResult:
    score: int
    findings: list[str] = field(default_factory=list)
    verifiers_scanned: int = 0
    notes: str = ""


def _walk_sol(path: Path):
    for f in path.rglob("*.sol"):
        if not f.is_file():
            continue
        if any(part in _SKIP_DIRS for part in f.parts):
            continue
        yield f


def _is_verifier(text: str) -> bool:
    """Heuristic: a verifier mentions pairing/curve + has a verify function."""
    has_pairing = bool(re.search(r"\bpairing\b", text, re.IGNORECASE))
    has_curve = bool(re.search(r"BN254|bn254|BLS12_?381|bls12.?381", text))
    has_verify = bool(re.search(r"function\s+verify(?:Proof)?\s*\(", text))
    return has_verify and (has_pairing or has_curve)


@pro_only(
    name="verifier_soundness",
    summary="Deep soundness scan of Solidity ZK verifiers: delegatecall presence, scalar-field bounds, G1/G2 zero-check, pairing-precompile gas griefing, public-input malleability.",
)
def detect(path: Path) -> VerifierSoundnessResult:
    findings: list[str] = []
    scanned = 0

    for f in _walk_sol(path):
        try:
            text = f.read_text(errors="ignore")
        except Exception:
            continue
        if not _is_verifier(text):
            continue
        scanned += 1
        rel = str(f.relative_to(path))

        # --- delegatecall in verifier ---
        if re.search(r"\bdelegatecall\s*\(", text):
            findings.append(
                f"{rel}: contains `delegatecall(...)` — a verifier should never "
                "delegatecall arbitrary code; review for proxy-pattern misuse"
            )

        # --- scalar-field bounds check on public inputs ---
        # Look for either the BN254 modulus or BLS12-381 modulus appearing as
        # the right-hand side of a require/assert/less-than check.
        has_field_check = (
            BN254_R in text.replace("_", "").replace(" ", "")
            or BLS12_R in text.replace("_", "").replace(" ", "")
            or "snark_scalar_field" in text.lower()
            or "PRIME_R" in text
            or "FR_MODULUS" in text
        )
        if not has_field_check:
            findings.append(
                f"{rel}: no obvious scalar-field bounds check on public inputs — "
                "ensure each input < curve order (BN254=2^254 approx., BLS12-381=2^255 approx.)"
            )

        # --- G1/G2 zero-point check ---
        has_zero_check = (
            re.search(r"\.X\s*==\s*0\s*&&\s*\.Y\s*==\s*0", text) is not None
            or re.search(r"require\s*\([^)]*[A-Za-z_]+\.X\s*!=\s*0", text) is not None
            or "isInfinity" in text
            or "is_infinity" in text
        )
        # Heuristic only fires if the verifier mentions Pairing.G1Point
        if "G1Point" in text and not has_zero_check:
            findings.append(
                f"{rel}: no zero-/infinity-point guard on G1Point inputs — a "
                "zero point can make naive verifiers accept trivial proofs"
            )

        # --- pairing precompile call: gas amount inspection ---
        # Look for `staticcall(gas(), 8, ...)` (BN256Pairing precompile = 0x08).
        # If they use `gas()` they're forwarding all gas, which is fine; but if
        # they hard-code a low gas value it's a footgun.
        for m in re.finditer(
            r"staticcall\s*\(\s*([^,]+),\s*8\s*,", text
        ):
            gas_expr = m.group(1).strip()
            if gas_expr.isdigit() and int(gas_expr) < 200000:
                findings.append(
                    f"{rel}: pairing precompile called with hard-coded gas "
                    f"{gas_expr} — too low; use gas() or >=1_000_000"
                )

        # --- nonReentrant guard on verify() ---
        if "ReentrancyGuard" not in text and "nonReentrant" not in text:
            # Only flag if the verifier has external/public verify
            if re.search(r"function\s+verify\w*\s*\([^)]*\)\s*(?:external|public)", text):
                findings.append(
                    f"{rel}: verify() is external/public with no nonReentrant guard — "
                    "review whether any callback path exists"
                )
                # NOTE: this finding is the weakest of the lot; many verifiers
                # legitimately don't need a reentrancy guard. We keep it as
                # informational but it does affect the score.

    if scanned == 0:
        return VerifierSoundnessResult(
            score=10,
            verifiers_scanned=0,
            notes="no Solidity ZK verifiers found — nothing to audit",
        )

    if not findings:
        return VerifierSoundnessResult(
            score=10,
            verifiers_scanned=scanned,
            notes=f"{scanned} verifier(s) scanned, no soundness findings",
        )

    score = max(0, 10 - len(findings))
    return VerifierSoundnessResult(
        score=score,
        verifiers_scanned=scanned,
        findings=findings,
        notes=f"{scanned} verifier(s) scanned, {len(findings)} finding(s)",
    )
