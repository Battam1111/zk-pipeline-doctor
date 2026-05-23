"""Pro detector: estimate circuit complexity across detected ZK ecosystems.

This detector is multi-file and cross-ecosystem on purpose; it touches:
  - Plonky3 AIR width / column counts (scanned from `Air for X` impl blocks)
  - SP1 program complexity (counts of `sp1_zkvm::*` syscalls + size of program/)
  - Compact circuit count (number of `circuit foo()` blocks across .compact files)
  - Noir constraint sizing hints (count of `assert*` calls + loop bounds)
  - Cairo M / Cairo function counts

The intent is to give Pro users an "is this circuit big and worth profiling?"
signal that the basic free-tier `language` detector does not provide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from zk_doctor.pro import pro_only


_SKIP_DIRS = {"node_modules", "target", "dist", "build", ".venv", "__pycache__", "vendor", ".git"}


@dataclass
class CircuitComplexityResult:
    score: int
    metrics: dict[str, int] = field(default_factory=dict)
    notes: str = ""
    findings: list[str] = field(default_factory=list)


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


@pro_only(
    name="circuit_complexity",
    summary="Estimate circuit size and constraint count across Plonky3 AIRs, SP1 programs, Compact circuits, Noir asserts, and Cairo functions (multi-file analysis).",
)
def detect(path: Path) -> CircuitComplexityResult:
    metrics: dict[str, int] = {}
    findings: list[str] = []

    # --- Compact circuit count ---
    compact_circuits = 0
    compact_pattern = re.compile(r"^\s*circuit\s+\w+", re.MULTILINE)
    for f in _walk(path, "*.compact"):
        compact_circuits += len(compact_pattern.findall(_safe_text(f)))
    if compact_circuits:
        metrics["compact_circuits"] = compact_circuits

    # --- Noir constraint hints: assert* + range patterns ---
    noir_asserts = 0
    noir_loops = 0
    assert_pattern = re.compile(r"\bassert\w*\s*\(")
    loop_pattern = re.compile(r"\bfor\s+\w+\s+in\s+\d+\.\.\d+")
    for f in _walk(path, "*.nr"):
        t = _safe_text(f)
        noir_asserts += len(assert_pattern.findall(t))
        noir_loops += len(loop_pattern.findall(t))
    if noir_asserts:
        metrics["noir_asserts"] = noir_asserts
    if noir_loops:
        metrics["noir_loops"] = noir_loops

    # --- Plonky3 AIR scan: `impl<...> Air<...> for X` and trace width ---
    plonky3_airs = 0
    plonky3_width_hint = 0
    air_pattern = re.compile(r"impl\s*<[^>]*>\s*Air\s*<", re.MULTILINE)
    width_pattern = re.compile(r"TRACE_WIDTH\s*[:=]\s*(\d+)|NUM_COLS\s*[:=]\s*(\d+)")
    for f in _walk(path, "*.rs"):
        t = _safe_text(f)
        plonky3_airs += len(air_pattern.findall(t))
        for m in width_pattern.finditer(t):
            try:
                plonky3_width_hint += int(m.group(1) or m.group(2) or 0)
            except ValueError:
                pass
    if plonky3_airs:
        metrics["plonky3_airs"] = plonky3_airs
    if plonky3_width_hint:
        metrics["plonky3_trace_width_sum"] = plonky3_width_hint

    # --- SP1 program complexity: count syscall surface in .rs in program/ subdir ---
    sp1_syscalls = 0
    sp1_pattern = re.compile(r"\bsp1_zkvm\s*::")
    for f in _walk(path, "*.rs"):
        if "program" in {p.name for p in f.parents}:
            sp1_syscalls += len(sp1_pattern.findall(_safe_text(f)))
    if sp1_syscalls:
        metrics["sp1_syscall_uses"] = sp1_syscalls

    # --- Cairo / Cairo M function counts ---
    cairo_fns = 0
    cairo_pattern = re.compile(r"^\s*fn\s+\w+", re.MULTILINE)
    for f in _walk(path, "*.cairo"):
        cairo_fns += len(cairo_pattern.findall(_safe_text(f)))
    if cairo_fns:
        metrics["cairo_functions"] = cairo_fns

    if not metrics:
        return CircuitComplexityResult(
            score=0,
            notes="no circuit complexity signals found (no .nr / .compact / .cairo / Plonky3 AIRs / SP1 program)",
        )

    # Heuristic scoring: a project with measurable complexity is healthier
    # than one with none; very-large complexity is fine on its own but flag
    # if total grows without test coverage (cross-detector hint).
    total = sum(metrics.values())
    if total >= 200:
        findings.append(
            f"high circuit complexity ({total} signals total) — recommend profiling proving time + memory"
        )
        score = 7
    elif total >= 50:
        score = 8
    elif total >= 10:
        score = 9
    else:
        score = 10

    notes_parts = [f"{k}={v}" for k, v in sorted(metrics.items())]
    notes = ", ".join(notes_parts) or "no signals"
    return CircuitComplexityResult(score=score, metrics=metrics, notes=notes, findings=findings)
