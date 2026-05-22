"""zk-doctor CLI entry point."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from zk_doctor.detectors import ci, docs, language, reproducibility, security, tests
from zk_doctor.report import format_json, format_markdown


app = typer.Typer(no_args_is_help=True, help="Diagnose ZK circuit projects for common health issues.")
console = Console()


@app.command()
def main(
    path: Path = typer.Argument(Path("."), help="Project directory to diagnose"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format (markdown|json)"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write report to file"),
    threshold: float = typer.Option(0.0, "--threshold", "-t", help="Exit nonzero if overall score < threshold"),
) -> None:
    """Diagnose the ZK project at PATH and emit a health report."""
    path = path.resolve()
    if not path.exists():
        console.print(f"[red]path not found: {path}[/]")
        raise typer.Exit(2)

    results = {
        "Language": language.detect(path),
        "Tests": tests.detect(path),
        "CI": ci.detect(path),
        "Documentation": docs.detect(path),
        "Security": security.detect(path),
        "Reproducibility": reproducibility.detect(path),
    }
    overall = sum(r.score for r in results.values()) / len(results)

    if format == "json":
        out = format_json(results, overall)
    else:
        out = format_markdown(results, overall)

    if output:
        output.write_text(out)
        console.print(f"[green]report saved to {output}[/]")
    else:
        if format == "markdown":
            console.print(out)
        else:
            console.print_json(out)

    if overall < threshold:
        raise typer.Exit(1)





@app.command(name="upgrade-info")
def upgrade_info() -> None:
    """Print pricing tiers + paid offerings."""
    from rich.console import Console
    from rich.table import Table
    c = Console()
    c.print("[bold]zk-pipeline-doctor — Tiered offerings[/]\n")
    t = Table(show_header=True, header_style="bold cyan")
    t.add_column("Tier")
    t.add_column("What you get")
    t.add_column("Price", justify="right")
    t.add_row("Free CLI (this)", "All 8 detectors, run locally", "[green]$0[/]")
    t.add_row("Free GitHub Action", "Drop-in CI integration", "[green]$0[/]")
    t.add_row("ZK Cookbook Bundle", "17 tutorials + code repos (ZIP)", "$15 once")
    t.add_row("Cookbook + Pro License", "Bundle + priority detector requests", "$49 once")
    t.add_row("$99 Pre-Flight Audit", "We run + narrate + review your repo", "$99 once")
    t.add_row("Bounty Radar Hobbyist", "Real-time Telegram alerts, 1 filter", "$19/mo")
    t.add_row("Bounty Radar Pro", "Unlimited filters + HMAC webhook", "$97/mo")
    t.add_row("Bounty Radar Team", "Shared Slack/Discord + 5 seats", "$497/mo")
    c.print(t)
    c.print("\n[dim]All payments via Polar.sh (Merchant of Record) · 14-day money-back.[/]")
    c.print("[dim]Pricing page: https://battam1111.github.io/midnight-zk-cookbook/pricing.html[/]")


if __name__ == "__main__":
    app()
