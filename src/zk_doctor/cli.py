"""zk-doctor — multi-ecosystem ZK project health audit CLI."""

from __future__ import annotations

import json as _json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from zk_doctor.detectors import ci, docs, language, reproducibility, security, tests as t_det
from zk_doctor.report import format_json, format_markdown


app = typer.Typer(
    name="zk-doctor",
    help="Diagnose the ZK project at PATH and emit a health report.",
    no_args_is_help=False,
    add_completion=True,
    invoke_without_command=False,
)


DETECTORS = {
    "language": language.detect,
    "tests": t_det.detect,
    "ci": ci.detect,
    "docs": docs.detect,
    "security": security.detect,
    "reproducibility": reproducibility.detect,
}


def _print_upgrade_table() -> None:
    """Print the pricing tier table (rich.Table). Shared by --upgrade-info."""
    c = Console()
    c.print("[bold]zk-pipeline-doctor — Tiered offerings[/]\n")
    t = Table(show_header=True, header_style="bold cyan")
    t.add_column("Tier")
    t.add_column("What you get")
    t.add_column("Price", justify="right")
    t.add_row("Free CLI (this)",        "All 8 detectors, run locally",       "[green]$0[/]")
    t.add_row("Free GitHub Action",     "Drop-in CI integration",             "[green]$0[/]")
    t.add_row("ZK Cookbook Bundle",     "17 tutorials + code repos (ZIP)",    "$15 once")
    t.add_row("Cookbook + Pro License", "Bundle + priority detector requests","$49 once")
    t.add_row("$99 Pre-Flight Audit",   "We run + narrate + review your repo","$99 once")
    t.add_row("Bounty Radar Hobbyist",  "Real-time Telegram alerts, 1 filter","$19/mo")
    t.add_row("Bounty Radar Pro",       "Unlimited filters + HMAC webhook",   "$97/mo")
    t.add_row("Bounty Radar Team",      "Shared Slack/Discord + 5 seats",     "$497/mo")
    c.print(t)
    c.print("\n[dim]All payments via Polar.sh (Merchant of Record) · 14-day money-back.[/]")
    c.print("[dim]Pricing page: https://battam1111.github.io/midnight-zk-cookbook/pricing.html[/]")


@app.callback(invoke_without_command=True)
def scan(
    ctx: typer.Context,
    path: Path = typer.Argument(Path("."), help="Project directory to diagnose"),
    output_format: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown | json"),
    output: Path = typer.Option(None, "--output", "-o", help="Write report to file (otherwise stdout)"),
    threshold: float = typer.Option(0.0, "--threshold", "-t", help="Exit nonzero if overall score < threshold"),
    upgrade_info: bool = typer.Option(False, "--upgrade-info", help="Print pricing tiers and exit"),
) -> None:
    """Diagnose the ZK project at PATH and emit a health report."""
    if upgrade_info:
        _print_upgrade_table()
        raise typer.Exit(0)

    if ctx.invoked_subcommand is not None:
        # A subcommand was invoked — defer to it
        return

    if not path.exists():
        typer.echo(f"path does not exist: {path}", err=True)
        raise typer.Exit(2)

    results = {}
    for name, fn in DETECTORS.items():
        try:
            results[name] = fn(path)
        except Exception as e:
            typer.echo(f"detector {name} failed: {e!r}", err=True)
            from zk_doctor.detectors.language import LanguageResult
            results[name] = LanguageResult(score=0, notes=f"error: {e!r}")

    scores = [r.score for r in results.values() if r.score is not None]
    overall = sum(scores) / max(1, len(scores))

    if output_format == "json":
        out = format_json(results, overall)
    else:
        out = format_markdown(results, overall)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(out)
        typer.echo(f"wrote {output}")
    else:
        typer.echo(out)

    if threshold > 0 and overall < threshold:
        typer.echo(f"FAIL: overall score {overall:.1f} < threshold {threshold:.1f}", err=True)
        raise typer.Exit(1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
