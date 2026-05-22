"""Check for hard-coded secrets, missing .gitignore patterns, untracked sensitive files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (RSA )?PRIVATE KEY-----"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI / Anthropic style
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),  # GitHub PAT
    re.compile(r"(?i)password\s*=\s*[\"'][^\"']{8,}[\"']"),
]

GITIGNORE_RECOMMENDED = {"node_modules", "target", "dist", "build", ".env", "*.key", "*.pem"}


@dataclass
class SecurityResult:
    score: int
    findings: list[str] = field(default_factory=list)
    notes: str = ""


def detect(path: Path) -> SecurityResult:
    """Scan a project for common security hygiene issues."""
    findings: list[str] = []
    skip_dirs = {"node_modules", "target", "dist", ".venv", "__pycache__", ".git"}

    # Scan small files for secret patterns
    for f in path.rglob("*"):
        if not f.is_file():
            continue
        if any(part in skip_dirs for part in f.parts):
            continue
        if f.stat().st_size > 200_000:  # skip large binary-ish files
            continue
        try:
            content = f.read_text(errors="ignore")
        except Exception:
            continue
        for pat in SECRET_PATTERNS:
            if pat.search(content):
                findings.append(f"possible secret in {f.relative_to(path)}: {pat.pattern[:40]}")
                break  # one finding per file is enough

    # Check .gitignore coverage
    gi = path / ".gitignore"
    if gi.is_file():
        gi_content = gi.read_text(errors="ignore")
        missing = [p for p in GITIGNORE_RECOMMENDED if p not in gi_content]
        if missing:
            findings.append(f".gitignore missing common patterns: {', '.join(missing[:4])}")
    else:
        findings.append("no .gitignore file")

    if not findings:
        return SecurityResult(score=10, notes="clean")

    score = max(0, 10 - len(findings) * 2)
    return SecurityResult(score=score, findings=findings, notes=f"{len(findings)} finding(s)")
