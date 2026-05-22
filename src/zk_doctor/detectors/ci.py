"""Check for GitHub Actions / GitLab CI / Circle CI configs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CIResult:
    score: int
    workflows: list[str] = field(default_factory=list)
    notes: str = ""


def detect(path: Path) -> CIResult:
    """Search for CI configuration files."""
    workflows: list[str] = []

    # GitHub Actions
    gh_dir = path / ".github" / "workflows"
    if gh_dir.is_dir():
        for f in gh_dir.iterdir():
            if f.suffix in (".yml", ".yaml") and f.is_file():
                workflows.append(str(f.relative_to(path)))

    # GitLab CI
    gl = path / ".gitlab-ci.yml"
    if gl.is_file():
        workflows.append(str(gl.relative_to(path)))

    # Circle CI
    cc = path / ".circleci" / "config.yml"
    if cc.is_file():
        workflows.append(str(cc.relative_to(path)))

    if not workflows:
        return CIResult(score=0, notes="no CI configuration found")

    score = 10 if len(workflows) >= 2 else 6
    return CIResult(score=score, workflows=workflows, notes=f"{len(workflows)} workflow file(s)")
