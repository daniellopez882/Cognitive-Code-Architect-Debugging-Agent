#!/usr/bin/env python3
"""
Code Review and Debugging Agent - Main Entry Point
"""

import asyncio
import os
import shutil
import sys
import tempfile

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from agents.graph import app
from utils.config_loader import load_config
from utils.logger import setup_logger

# Load environment variables
load_dotenv()

console = Console()
logger = setup_logger(__name__)


def resolve_target(repository_url: str) -> tuple[str, str, bool]:
    """
    Decide where the code under review lives.

    Returns ``(repository_url, local_path, is_temporary)``. An existing
    directory is reviewed in place (``repository_url`` becomes ``"local"``);
    anything else is treated as a clone URL and gets a fresh temporary
    directory, which the caller removes afterwards.

    The command used to pass ``local_path=""`` for every target, so the
    initialisation node tried to clone into an empty path and failed with
    ``FileNotFoundError`` before any analysis ran -- for a URL and for a
    directory alike. The CLI could not review anything.
    """
    if os.path.isdir(repository_url):
        return "local", os.path.abspath(repository_url), False
    return repository_url, tempfile.mkdtemp(prefix="review-"), True


@click.group()
def cli():
    """Code Review and Debugging Agent CLI"""
    pass


@cli.command()
@click.argument("repository_url")
@click.option(
    "--scope",
    default="full",
    type=click.Choice(["full", "branch", "files", "diff", "security_only", "performance_only"]),
    help="Analysis scope",
)
@click.option("--branch", default=None, help="Target branch for analysis")
@click.option("--files", default=None, help="Comma-separated list of files to analyze")
@click.option(
    "--auto-fix/--no-auto-fix",
    default=False,
    help=(
        "Ask the model to propose fixes for auto-fixable findings. Proposals go "
        "into the report; nothing is written to the repository."
    ),
)
@click.option(
    "--severity",
    default="medium",
    type=click.Choice(["critical", "high", "medium", "low", "info"]),
    help="Minimum severity threshold",
)
@click.option("--output", default="./reports", help="Output directory for reports")
@click.option(
    "--format",
    default="markdown",
    type=click.Choice(["markdown", "json", "html", "all"]),
    help="Report format",
)
def review(repository_url, scope, branch, files, auto_fix, severity, output, format):
    """
    Review a code repository.
    """
    console.print(f"[bold blue]Starting code review for:[/bold blue] {repository_url}")

    # Prepare initial state
    target_files = files.split(",") if files else None
    repository_url, local_path, is_temporary = resolve_target(repository_url)

    initial_state = {
        "repository_url": repository_url,
        "local_path": local_path,
        "review_scope": scope,
        "target_branch": branch,
        "target_files": target_files,
        "severity_threshold": severity,
        "auto_fix_enabled": auto_fix,
        "messages": [],
        "errors": [],
        "static_analysis_findings": [],
        "pattern_analysis_findings": [],
        "security_findings": [],
        "performance_findings": [],
        "testing_findings": [],
        "logic_findings": [],
        "files_analyzed": 0,
        "total_files": 0,
        "all_findings": [],
        "prioritized_issues": [],
        "quick_wins": [],
        "generated_fixes": [],
        "markdown_report": "",
        "json_report": {},
        "github_issues": [],
        "current_step": "started",
        "analysis_start_time": 0.0,
        "user_feedback": [],
        "skip_categories": [],
    }

    # Run analysis
    try:
        ok = asyncio.run(run_analysis(initial_state, output, format))
    finally:
        if is_temporary:
            shutil.rmtree(local_path, ignore_errors=True)
    if not ok:
        sys.exit(1)


async def run_analysis(initial_state: dict, output_dir: str, report_format: str) -> bool:
    """Execute the code review analysis. Returns False if it did not complete."""

    # app is the compiled graph from graph.py

    config = {"configurable": {"thread_id": "review-session"}}

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
    ) as progress:
        analysis_task = progress.add_task("[cyan]Analyzing repository...", total=None)

        try:
            final_state = initial_state
            async for event in app.astream(initial_state, config):
                # The event in astream is usually a dict {node_name: state_delta}
                # But here we assume a simpler streaming or standard invoke result
                # For simplicity in this demo, we'll just track the current step
                if isinstance(event, dict):
                    for _node, state in event.items():
                        if "current_step" in state:
                            current_step = state["current_step"]
                            progress.update(
                                analysis_task,
                                description=f"[cyan]{current_step.replace('_', ' ').title()}",
                            )
                        final_state.update(state)

            progress.update(analysis_task, description="[green]Analysis complete!")

            # Display summary
            display_summary(final_state)

            # Save reports
            save_reports(final_state, output_dir, report_format)
            return True

        except Exception as e:
            # A run that did not finish must not exit 0: the caller would
            # read an absent report as a clean one.
            console.print(f"[red]Error during analysis:[/red] {e!s}")
            return False
            logger.error(f"Analysis failed: {e}", exc_info=True)


def display_summary(state: dict):
    """Display analysis summary."""
    console.print("\n" + "=" * 60)
    console.print("[bold green]Analysis Summary[/bold green]")
    console.print("=" * 60 + "\n")

    all_findings = state.get("prioritized_issues", [])

    # Count by severity
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

    for finding in all_findings:
        severity = finding.get("severity", "info")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    # Display counts
    console.print(f"Total Issues: [bold]{len(all_findings)}[/bold]\n")
    console.print(f"🔴 Critical: {severity_counts['critical']}")
    console.print(f"🟠 High: {severity_counts['high']}")
    console.print(f"🟡 Medium: {severity_counts['medium']}")
    console.print(f"🟢 Low: {severity_counts['low']}")
    console.print(f"ℹ️  Info: {severity_counts['info']}\n")

    proposals = state.get("generated_fixes", [])
    if proposals:
        usable = sum(1 for p in proposals if p.get("status") == "proposed")
        console.print(
            f"Proposed fixes: [bold]{usable}[/bold] of {len(proposals)} usable "
            "(in the report; not applied)\n"
        )

    # Top issues
    if all_findings:
        console.print("[bold]Top 5 Priority Issues:[/bold]")
        for i, finding in enumerate(all_findings[:5], 1):
            console.print(
                f"{i}. [{finding['severity'].upper()}] {finding.get('title', 'Untitled')}"
            )
            console.print(f"   📄 {finding.get('file', 'Unknown file')}:{finding.get('line', '?')}")
            console.print()


def save_reports(state: dict, output_dir: str, report_format: str):
    """Save analysis reports."""
    os.makedirs(output_dir, exist_ok=True)

    if report_format in ["markdown", "all"]:
        markdown_path = os.path.join(output_dir, "code_review_report.md")
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(state.get("markdown_report", "No report generated"))
        console.print(f"\n✓ Markdown report saved to: [blue]{markdown_path}[/blue]")

    if report_format in ["json", "all"]:
        import json

        json_path = os.path.join(output_dir, "code_review_report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(state.get("json_report", {}), f, indent=2)
        console.print(f"✓ JSON report saved to: [blue]{json_path}[/blue]")

    console.print("\n[bold green]Analysis complete! 🎉[/bold green]")


@cli.command()
@click.argument("config_file")
def validate_config(config_file):
    """Validate a .codeguardian.yml configuration file."""
    try:
        config = load_config(config_file)
        console.print("[green]✓ Configuration is valid[/green]")
        console.print("\nLoaded configuration:")
        import yaml

        console.print(yaml.dump(config, default_flow_style=False))
    except Exception as e:
        console.print(f"[red]✗ Configuration error:[/red] {e!s}")


@cli.command()
def version():
    """Display version information."""
    console.print("[bold]Code Review Agent v1.0.0[/bold]")
    console.print("Built with LangChain, LangGraph, and Google Gemini")


if __name__ == "__main__":
    cli()
