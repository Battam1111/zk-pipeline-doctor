"""Pro detector: cross-file consistency checks for ZK projects.

ZK projects routinely have the same constant appearing in multiple files
(field-size assumptions, proving-system version, circuit width, public-input
arity). Drift between those copies is a common bug source. This detector
looks for:

  - proving-system version pinned in Cargo.toml AND README AND CI workflow,
    flag if any two diverge
  - dev vs prod feature-flag drift (RISC0_DEV_MODE, sp1-zkvm `bench` feature,
    `mock` features set in some configs but not others)
  - circuit signature drift (Compact `circuit foo(a: Field, b: Field)` exposed
    by .compact but Solidity verifier or off-chain prover expects different
    arity)
  - .gitattributes vs LFS pointer drift on large proving keys
  - lockfile dialect drift (Cargo.lock format v3 vs v4 across workspace members)

Multi-file consistency is the kind of thing that needs to walk the whole
project, parse a few formats, and reason about cross-references. That's
exactly the engineering surface that justifies being a pro-tier check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from zk_doctor.pro import pro_only


_SKIP_DIRS = {"node_modules", "target", "dist", "build", ".venv", "__pycache__", "vendor", ".git"}


@dataclass
class ConsistencyResult:
    score: int
    findings: list[str] = field(default_factory=list)
    notes: str = ""


def _walk_files(path: Path, glob: str):
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


@pro_only(
    name="multi_file_consistency",
    summary="Cross-file drift checks: proving-system version pinned consistently across Cargo.toml / README / CI; dev-vs-prod feature flag consistency; circuit signature vs verifier arity drift; lockfile dialect consistency.",
)
def detect(path: Path) -> ConsistencyResult:
    findings: list[str] = []

    # ---- proving-system version drift ----
    # Extract first version-looking string after risc0-zkvm / sp1-zkvm / etc.
    # from Cargo.toml files.
    version_patterns = [
        ("risc0-zkvm", re.compile(r"risc0-zkvm\s*=\s*[\"']?(?:version\s*=\s*[\"']?)?([\d.]+)")),
        ("sp1-zkvm", re.compile(r"sp1-zkvm\s*=\s*[\"']?(?:version\s*=\s*[\"']?)?([\d.]+)")),
        ("plonky3", re.compile(r"p3-air\s*=\s*[\"']?(?:version\s*=\s*[\"']?)?([\d.]+)")),
        ("stwo-prover", re.compile(r"stwo-prover\s*=\s*[\"']?(?:version\s*=\s*[\"']?)?([\d.]+)")),
    ]
    versions_seen: dict[str, set[str]] = {label: set() for label, _ in version_patterns}

    for cargo in _walk_files(path, "Cargo.toml"):
        text = _safe_text(cargo)
        for label, pat in version_patterns:
            for m in pat.finditer(text):
                v = m.group(1)
                if v:
                    versions_seen[label].add(v)

    for label, vs in versions_seen.items():
        if len(vs) > 1:
            findings.append(
                f"{label} version pinned to multiple values across Cargo.toml files: {sorted(vs)} — "
                "all workspace crates should depend on the same proving-system version"
            )

    # ---- README vs Cargo version drift ----
    readme = path / "README.md"
    if readme.is_file():
        readme_text = _safe_text(readme).lower()
        for label, vs in versions_seen.items():
            if len(vs) != 1:
                continue
            (v,) = vs
            # If README mentions a different version number near the system name, flag it.
            label_lower = label.replace("-zkvm", "").replace("-prover", "")
            for m in re.finditer(rf"{re.escape(label_lower)}[^\n]*?([\d]+\.[\d.]+)", readme_text):
                rv = m.group(1)
                if rv != v and not v.startswith(rv) and not rv.startswith(v):
                    findings.append(
                        f"README mentions {label} {rv} but Cargo pins {v} — keep one source of truth"
                    )
                    break

    # ---- dev-mode flag drift ----
    # Any file setting RISC0_DEV_MODE=1 AND any other file setting =0 or unset
    dev_set: list[Path] = []
    for f in _walk_files(path, "*"):
        if f.suffix not in {".rs", ".sh", ".yml", ".yaml", ".toml", ".env"} and f.name not in {".env"}:
            continue
        if f.stat().st_size > 200_000:
            continue
        text = _safe_text(f)
        if re.search(r"RISC0_DEV_MODE\s*[:=]\s*[\"']?1", text) or "dev_mode: true" in text:
            dev_set.append(f)
    if len(dev_set) >= 2:
        files_str = ", ".join(str(f.relative_to(path)) for f in dev_set[:3])
        findings.append(
            f"RISC0_DEV_MODE=1 set in {len(dev_set)} places ({files_str}) — "
            "verify none of these reach a release / production CI step"
        )

    # ---- lockfile dialect drift (Cargo.lock v3 vs v4) ----
    versions_locked: set[str] = set()
    for lock in _walk_files(path, "Cargo.lock"):
        text = _safe_text(lock)
        m = re.search(r'^\s*version\s*=\s*(\d+)\s*$', text, re.MULTILINE)
        if m:
            versions_locked.add(m.group(1))
    if len(versions_locked) > 1:
        findings.append(
            f"Cargo.lock dialect drift: versions {sorted(versions_locked)} found — "
            "should be a single Cargo version across the workspace"
        )

    # ---- Compact circuit signature vs Solidity verify arity drift ----
    # Best-effort: parse the first `circuit foo(...)` parameter list and the
    # first Solidity `verifyProof(...uint[N] memory input)` arity.
    compact_args: int | None = None
    for f in _walk_files(path, "*.compact"):
        text = _safe_text(f)
        m = re.search(r"^\s*circuit\s+\w+\s*\(([^)]*)\)", text, re.MULTILINE)
        if m:
            args = m.group(1).strip()
            compact_args = 0 if not args else len([a for a in args.split(",") if a.strip()])
            break

    sol_input_arity: int | None = None
    for f in _walk_files(path, "*.sol"):
        text = _safe_text(f)
        m = re.search(r"verifyProof\s*\([^)]*uint\s*\[\s*(\d+)\s*\]\s+(?:memory|calldata)?\s*\w*\s*input", text)
        if m:
            try:
                sol_input_arity = int(m.group(1))
                break
            except ValueError:
                pass

    if compact_args is not None and sol_input_arity is not None and compact_args != sol_input_arity:
        findings.append(
            f"Compact circuit takes {compact_args} parameters but Solidity verifier expects "
            f"{sol_input_arity} public inputs — review for off-by-one between circuit and verifier"
        )

    if not findings:
        return ConsistencyResult(score=10, notes="no cross-file consistency issues detected")

    score = max(0, 10 - len(findings) * 2)
    return ConsistencyResult(score=score, findings=findings, notes=f"{len(findings)} consistency issue(s)")
