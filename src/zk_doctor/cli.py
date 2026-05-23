"""zk-doctor — multi-ecosystem ZK project health audit CLI.

v0.3.0 introduces a tiered model: 6 free detectors + 4 Pro detectors gated
behind a license key validated via Polar's customer-portal API.

CLI surface (backwards-compatible with v0.2.x):

  zk-doctor [PATH] [flags]              # diagnose (default)
  zk-doctor activate <license-key>      # validate + cache key
  zk-doctor license-status              # show tier
  zk-doctor --upgrade-info              # pricing tiers
  zk-doctor --explain-pro               # what Pro adds

The first positional argument is either a known subcommand name or a path.
We sniff `sys.argv[1]` before typer dispatches so the path-style invocation
keeps working without a subcommand prefix.
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from zk_doctor import license as _lic
from zk_doctor.detectors import (
    ci,
    circuit_complexity,
    docs,
    language,
    multi_file_consistency,
    proving_system_pitfalls,
    reproducibility,
    security,
    tests,
    verifier_soundness,
)
from zk_doctor.pro import UPGRADE_URL, explain_pro_lines
from zk_doctor.report import format_json, format_markdown


# Two separate Typer apps: one for diagnose (the default, backwards-compatible
# path-positional command), and a router app that swaps in the subcommand if
# the first argv looks like one. The router is the public entrypoint.
diagnose_app = typer.Typer(no_args_is_help=False, help="Diagnose ZK circuit projects for common health issues.")
subcommand_app = typer.Typer(no_args_is_help=True, help="zk-doctor subcommands.")

console = Console()


def _print_upgrade_table() -> None:
    """Print the pricing tier table. Shared by --upgrade-info flag."""
    console.print("[bold]zk-pipeline-doctor — Tiered offerings[/]\n")
    t = Table(show_header=True, header_style="bold cyan")
    t.add_column("Tier")
    t.add_column("What you get")
    t.add_column("Price", justify="right")
    t.add_row("Free CLI (this)",        "All 6 baseline detectors, run locally",  "[green]$0[/]")
    t.add_row("Free GitHub Action",     "Drop-in CI integration",                 "[green]$0[/]")
    t.add_row("ZK Cookbook Bundle",     "17 tutorials + code repos (ZIP)",        "$15 once")
    t.add_row("Cookbook + Pro License", "Bundle + priority detector requests",    "$49 once")
    t.add_row("zk-doctor Pro",          "+4 deep detectors",                      "$15/mo")
    t.add_row("$99 Pre-Flight Audit",   "We run + narrate + review your repo",    "$99 once")
    t.add_row("Bounty Radar Hobbyist",  "Real-time Telegram alerts, 1 filter",    "$19/mo")
    t.add_row("Bounty Radar Pro",       "Unlimited filters + HMAC webhook",       "$97/mo")
    t.add_row("Bounty Radar Team",      "Shared Slack/Discord + 5 seats",         "$497/mo")
    console.print(t)
    console.print("\n[dim]All payments via Polar.sh (Merchant of Record) · 14-day money-back.[/]")
    console.print("[dim]Pricing page: https://battam1111.github.io/midnight-zk-cookbook/pricing.html[/]")


# ---------- diagnose (default) command ----------

@diagnose_app.command()
def diagnose(
    path: Path = typer.Argument(Path("."), help="Project directory to diagnose"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format (markdown|json)"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write report to file"),
    threshold: float = typer.Option(0.0, "--threshold", "-t", help="Exit nonzero if overall score < threshold"),
    upgrade_info: bool = typer.Option(False, "--upgrade-info", help="Print pricing tiers and exit"),
    explain_pro: bool = typer.Option(False, "--explain-pro", help="List what Pro adds and exit"),
) -> None:
    """Diagnose the ZK project at PATH and emit a health report."""
    if upgrade_info:
        _print_upgrade_table()
        raise typer.Exit(0)
    if explain_pro:
        for line in explain_pro_lines():
            console.print(line)
        raise typer.Exit(0)

    path = path.resolve()
    if not path.exists():
        console.print(f"[red]path not found: {path}[/]")
        raise typer.Exit(2)

    # --- run all detectors; pro ones return ProLocked on free tier ---
    results = {
        "Language":                 language.detect(path),
        "Tests":                    tests.detect(path),
        "CI":                       ci.detect(path),
        "Documentation":            docs.detect(path),
        "Security":                 security.detect(path),
        "Reproducibility":          reproducibility.detect(path),
        # --- Pro tier (locked unless `zk-doctor activate <key>` succeeded) ---
        "Circuit Complexity":       circuit_complexity.detect(path),
        "Proving-System Pitfalls":  proving_system_pitfalls.detect(path),
        "Verifier Soundness":       verifier_soundness.detect(path),
        "Multi-File Consistency":   multi_file_consistency.detect(path),
    }

    is_pro = _lic.is_pro()
    if is_pro:
        scored_keys = list(results.keys())
    else:
        scored_keys = [
            "Language", "Tests", "CI", "Documentation", "Security", "Reproducibility",
        ]
    overall = sum(results[k].score for k in scored_keys) / len(scored_keys)

    if format == "json":
        out = format_json(results, overall, pro=is_pro)
    else:
        out = format_markdown(results, overall, pro=is_pro)

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


# ---------- subcommands ----------

@subcommand_app.command()
def activate(
    license_key: str = typer.Argument(..., help="Polar-issued zk-doctor Pro license key"),
) -> None:
    """Validate a license key with Polar and cache it locally for future runs."""
    console.print(f"[cyan]Validating key with Polar...[/]")
    validated = _lic.verify_license_key(license_key)
    if validated is None:
        console.print(
            "[red]X[/] License key did not validate. Possible reasons:\n"
            "  - key is wrong, revoked, or for a different organization\n"
            "  - Polar API is unreachable (check internet connectivity)\n"
            "  - activation limit on this benefit has been reached\n"
            f"\nPurchase or check status: {UPGRADE_URL}"
        )
        raise typer.Exit(1)

    info = _lic.current_license()
    console.print(f"[green]OK[/] License activated.")
    console.print(f"  Tier:          [bold]{info.tier}[/]")
    console.print(f"  Key:           {info.key_display}")
    if info.activation_id:
        console.print(f"  Activation ID: {info.activation_id}")
    console.print(f"  Cached at:     {_dt.datetime.fromtimestamp(info.cached_at).isoformat(timespec='seconds')}")
    console.print(f"\nRun `zk-doctor .` from any project to use Pro detectors.")


@subcommand_app.command("license-status")
def license_status() -> None:
    """Show the current license tier and which detectors are unlocked."""
    info = _lic.current_license()
    if info.tier == "free":
        console.print("[yellow]Free tier.[/] 6 baseline detectors active; 4 Pro detectors locked.")
        console.print(f"Upgrade: {UPGRADE_URL}")
        console.print("After purchase, run: [bold]zk-doctor activate <license-key>[/]")
        return

    console.print(f"[green]Pro tier active.[/] All 10 detectors unlocked.")
    console.print(f"  Key:           {info.key_display}")
    if info.activation_id:
        console.print(f"  Activation ID: {info.activation_id}")
    cached = _dt.datetime.fromtimestamp(info.cached_at).isoformat(timespec="seconds")
    console.print(f"  Cached at:     {cached}")
    console.print(f"  Cache file:    {_lic.CACHE_DB}")


# ---------- router ----------

SUBCOMMAND_NAMES = {"activate", "license-status"}


def app(argv: list[str] | None = None) -> None:
    """Public entrypoint. Routes to a subcommand if argv[1] matches, else
    falls through to the diagnose command (so `zk-doctor /path` keeps working)."""
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    # Routing rule: if the first non-flag argv element is a known subcommand
    # name, run the subcommand app; otherwise the diagnose app.
    first = next((a for a in argv if not a.startswith("-")), None)
    if first in SUBCOMMAND_NAMES:
        subcommand_app(argv)
    else:
        diagnose_app(argv)


if __name__ == "__main__":
    app()
