"""Pro-tier gating utilities.

The free tier keeps every detector that shipped in v0.2.x. The pro tier adds
four new "deep" detectors (circuit_complexity, proving_system_pitfalls,
verifier_soundness, multi_file_consistency). When a non-licensed user runs
the CLI, the pro detectors short-circuit to a `PRO_LOCKED_RESULT` placeholder
so the rest of the report still renders.

Everything routes through `pro_only()`. Decorate a `detect(path)` function
with it and the body only runs when `license.is_pro()` is true.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from zk_doctor import license as _lic


UPGRADE_URL = "https://polar.sh/Battam1111/zk-doctor-pro"
PRO_LOCK_NOTE = (
    "Locked. Run `zk-doctor activate <license-key>` after purchase at "
    + UPGRADE_URL
    + " — or `zk-doctor --explain-pro` for what this unlocks."
)


@dataclass
class ProLocked:
    """Sentinel detector result returned when the user is on the free tier."""
    score: int = 0
    locked: bool = True
    name: str = "(pro detector)"
    notes: str = PRO_LOCK_NOTE
    findings: list[str] = field(default_factory=list)


# Registry of pro detectors so `--explain-pro` can introspect what gets unlocked.
# Populated by the @pro_only decorator at import time.
PRO_DETECTORS: list[dict[str, str]] = []


def pro_only(name: str, summary: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a `detect(path)` function as pro-tier.

    `name` is the user-visible label (shown in the report and in --explain-pro).
    `summary` is one sentence explaining what the detector checks; used by
    --explain-pro for marketing copy and by ProLocked.notes for the gated path.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        PRO_DETECTORS.append({"name": name, "summary": summary, "func": fn.__module__})

        @wraps(fn)
        def wrapper(path: Path, *args: Any, **kwargs: Any) -> Any:
            if not _lic.is_pro():
                locked = ProLocked(name=name)
                # Customize notes with the specific summary for nicer UX
                locked.notes = (
                    f"Locked. {summary} "
                    f"Upgrade: {UPGRADE_URL} — `zk-doctor --explain-pro` for the full list."
                )
                return locked
            return fn(path, *args, **kwargs)

        wrapper.__pro_only__ = True       # type: ignore[attr-defined]
        wrapper.__pro_name__ = name       # type: ignore[attr-defined]
        wrapper.__pro_summary__ = summary # type: ignore[attr-defined]
        return wrapper

    return decorator


def explain_pro_lines() -> list[str]:
    """Lines describing what Pro unlocks. Used by `--explain-pro`."""
    out = [
        "zk-doctor Pro adds 4 deep cross-ecosystem detectors on top of the free 6.",
        "",
        "Free tier (always available):",
        "  - language        (which ZK ecosystems are present)",
        "  - tests           (test files + ratio)",
        "  - ci              (GitHub Actions / GitLab / Circle configs)",
        "  - docs            (README + examples + docs/)",
        "  - security        (secret patterns + .gitignore hygiene)",
        "  - reproducibility (lockfiles + toolchain pins)",
        "",
        "Pro tier (requires license key — purchase: " + UPGRADE_URL + "):",
    ]
    for d in PRO_DETECTORS:
        out.append(f"  - {d['name']:25s} {d['summary']}")
    out += [
        "",
        "Activate after purchase:  zk-doctor activate <license-key>",
        "Check status:             zk-doctor license-status",
    ]
    return out
