"""Check for test directory and test file presence."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TestsResult:
    score: int
    test_dirs: list[str] = field(default_factory=list)
    test_files: int = 0
    notes: str = ""


def detect(path: Path) -> TestsResult:
    """Look for tests/, test/, __tests__/ directories and *_test.*, *.spec.*, test_*.* files."""
    dirs: list[str] = []
    for candidate in ("tests", "test", "__tests__", "spec"):
        d = path / candidate
        if d.is_dir():
            dirs.append(str(d.relative_to(path)))

    n = 0
    skip_dirs = {"node_modules", "target", "dist", "build", ".venv", "__pycache__"}
    for pattern in ("*_test.*", "*.spec.*", "test_*.*", "*.test.*"):
        for f in path.rglob(pattern):
            if any(part in skip_dirs for part in f.parts):
                continue
            if f.is_file():
                n += 1

    if n == 0 and not dirs:
        return TestsResult(score=0, notes="no test files or tests/ directory found")
    if n < 3:
        return TestsResult(score=4, test_dirs=dirs, test_files=n, notes=f"sparse: {n} test file(s)")
    if n < 10:
        return TestsResult(score=7, test_dirs=dirs, test_files=n, notes=f"{n} test file(s)")
    return TestsResult(score=10, test_dirs=dirs, test_files=n, notes=f"strong test suite: {n} test files")
