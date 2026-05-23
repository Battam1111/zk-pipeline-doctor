"""Format detector results as markdown or JSON.

v0.3.0: aware of ProLocked sentinels so pro-tier detectors render as a
distinct "locked" row instead of looking like a real 0/10 failure.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any


def _is_locked(r: Any) -> bool:
    return bool(getattr(r, "locked", False))


def format_markdown(results: dict[str, Any], overall: float, pro: bool = False) -> str:
    lines = ["# zk-doctor report", ""]
    tier = "Pro" if pro else "Free"
    lines.append(f"**Overall score: {overall:.1f}/10**  ({tier} tier)")
    lines.append("")
    lines.append("| Dimension | Score | Notes |")
    lines.append("|---|---|---|")
    for name, r in results.items():
        if _is_locked(r):
            lines.append(f"| {name} | _locked_ | {r.notes} |")
        else:
            lines.append(f"| {name} | {r.score}/10 | {r.notes} |")
    lines.append("")
    lines.append("## Recommended fixes (priority order)")
    lines.append("")
    # Sort low scores first, excluding locked rows
    actionable = [(n, r) for n, r in results.items() if not _is_locked(r)]
    sorted_low = sorted(actionable, key=lambda kv: kv[1].score)
    for name, r in sorted_low:
        if r.score >= 8:
            continue
        lines.append(f"### {name} ({r.score}/10)")
        lines.append(f"- {r.notes}")
        if getattr(r, "findings", None):
            for f in r.findings[:5]:
                lines.append(f"  - {f}")
        lines.append(f"- See https://github.com/Battam1111/zk-pipeline-doctor#detected-dimensions for guidance.")
        lines.append("")

    # If on the free tier, surface a single-line upsell at the end (not in
    # every row — that's spammy). Only renders if at least one pro detector
    # is locked.
    if not pro and any(_is_locked(r) for r in results.values()):
        lines.append("---")
        lines.append("")
        lines.append("**Pro tier locked.** Run `zk-doctor --explain-pro` to see what unlocking adds.")
        lines.append("")
    return "\n".join(lines)


def _serialize(r: Any) -> dict[str, Any]:
    """Convert a detector result to a JSON-safe dict."""
    if is_dataclass(r):
        return asdict(r)
    if isinstance(r, dict):
        return r
    return {"repr": repr(r)}


def format_json(results: dict[str, Any], overall: float, pro: bool = False) -> str:
    blob = {
        "overall_score": round(overall, 2),
        "tier": "pro" if pro else "free",
        "dimensions": {name: _serialize(r) for name, r in results.items()},
    }
    return json.dumps(blob, indent=2, default=str)
