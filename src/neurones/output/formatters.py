"""Rich output formatters for headless CLI mode."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from neurones.models.result import AgentResult


def format_comparison_table(results: list[AgentResult], console: Console) -> None:
    """Display agent results in a side-by-side Rich table."""
    table = Table(
        title="Agent Comparison",
        show_header=True,
        header_style="bold",
        expand=True,
        padding=(0, 1),
    )

    table.add_column("Agent", style="bold", width=12)
    table.add_column("Status", width=14)
    table.add_column("Retries", width=8, justify="center")
    table.add_column("Time", width=8, justify="right")
    table.add_column("Output", ratio=1)

    for result in results:
        # Status styling
        label = result.status_label
        if label.startswith("SUCCESS"):
            status_style = "status.success"
        elif label == "RATE_LIMITED":
            status_style = "status.rate_limited"
        elif label == "TIMEOUT":
            status_style = "status.timeout"
        elif label == "FAILED":
            status_style = "status.failed"
        else:
            status_style = "dim"

        agent_style = f"agent.{result.agent_name}" if result.agent_name in ("claude", "gemini", "codex") else "bold"

        output_text = result.output[:500] if result.output else result.stderr[:200]
        if len(result.output) > 500:
            output_text += "..."

        retries_text = str(result.retries) if result.retries > 0 else "-"

        table.add_row(
            Text(result.agent_name, style=agent_style),
            Text(result.status_label, style=status_style),
            retries_text,
            f"{result.duration_seconds:.1f}s",
            output_text,
        )

    console.print(table)


def format_agent_result(result: AgentResult, console: Console) -> None:
    """Display a single agent result in a Rich panel."""
    label = result.status_label
    if label.startswith("SUCCESS"):
        status_style = "green"
    elif label == "RATE_LIMITED":
        status_style = "#ff8800"
    elif label == "TIMEOUT":
        status_style = "yellow"
    elif label == "FAILED":
        status_style = "red"
    else:
        status_style = "grey"

    retries_info = f", {result.retries} retries" if result.retries > 0 else ""
    title = f"{result.agent_name} [{label}] ({result.duration_seconds:.1f}s{retries_info})"

    panel = Panel(
        result.output or result.stderr or "[dim]No output[/dim]",
        title=title,
        border_style=status_style,
        expand=True,
    )
    console.print(panel)


def format_orchestration_result(
    original_prompt: str,
    results: list[AgentResult],
    final_output: str,
    console: Console,
) -> None:
    """Display the full orchestration result."""
    console.print(Panel(
        f"[bold]{original_prompt}[/bold]",
        title="Task",
        border_style="blue",
    ))

    if results:
        console.print("\n[dim]Agent Results:[/dim]")
        for result in results:
            format_agent_result(result, console)

    console.print(Panel(
        final_output,
        title="Synthesized Result",
        border_style="green",
        expand=True,
    ))
