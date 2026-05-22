"""Check documentation presence and quality."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocsResult:
    score: int
    readme_words: int = 0
    has_examples: bool = False
    notes: str = ""


def detect(path: Path) -> DocsResult:
    readme = None
    for name in ("README.md", "README.rst", "readme.md", "Readme.md"):
        p = path / name
        if p.is_file():
            readme = p
            break

    examples = (path / "examples").is_dir()
    docs_dir = (path / "docs").is_dir()

    if not readme:
        return DocsResult(score=0, notes="no README found")

    text = readme.read_text(errors="ignore")
    word_count = len(text.split())

    if word_count < 50:
        score = 2
    elif word_count < 200:
        score = 5
    elif word_count < 600:
        score = 7
    else:
        score = 9

    if examples:
        score = min(10, score + 1)

    notes_parts = [f"README {word_count} words"]
    if examples:
        notes_parts.append("examples/ ✓")
    if docs_dir:
        notes_parts.append("docs/ ✓")
    notes = ", ".join(notes_parts)

    return DocsResult(score=score, readme_words=word_count, has_examples=examples, notes=notes)
