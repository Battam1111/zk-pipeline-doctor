"""Format detector results as markdown or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any


def format_markdown(results: dict[str, Any], overall: float) -> str:
    lines = ["# zk-doctor report", ""]
    lines.append(f"**Overall score: {overall:.1f}/10**")
    lines.append("")
    lines.append("| Dimension | Score | Notes |")
    lines.append("|---|---|---|")
    for name, r in results.items():
        lines.append(f"| {name} | {r.score}/10 | {r.notes} |")
    lines.append("")
    lines.append("## Recommended fixes (priority order)")
    lines.append("")
    sorted_low = sorted(results.items(), key=lambda kv: kv[1].score)
    for name, r in sorted_low:
        if r.score >= 8:
            continue
        lines.append(f"### {name} ({r.score}/10)")
        lines.append(f"- {r.notes}")
        lines.append(f"- See https://github.com/Battam1111/zk-pipeline-doctor#detected-dimensions for guidance.")
        lines.append("")
    return "\n".join(lines)


def format_json(results: dict[str, Any], overall: float) -> str:
    blob = {
        "overall_score": round(overall, 2),
        "dimensions": {name: asdict(r) for name, r in results.items()},
    }
    return json.dumps(blob, indent=2, default=str)
