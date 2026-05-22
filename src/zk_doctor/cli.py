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


if __name__ == "__main__":
    app()
