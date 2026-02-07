"""Status command — nr status."""

from __future__ import annotations

import asyncio

import click

from neurones import __version__
from neurones.output.console import console


@click.command()
def status() -> None:
    """Show detected agents and their status."""
    asyncio.run(_status())


async def _status() -> None:
    """Display detected agents in a Rich table."""
    from rich.table import Table

    from neurones.adapters.detector import AgentDetector
    from neurones.config import load_config

    config = load_config()

    with console.status("[status.running]Detecting agents...[/status.running]"):
        detector = AgentDetector()
        detected = await detector.detect_all()

    console.print(f"\n[header]Neurones v{__version__}[/header]\n")

    if not detected:
        console.print("[status.failed]No AI CLI agents detected.[/status.failed]")
        console.print("Install at least one of: claude, gemini, codex\n")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Agent", style="bold")
    table.add_column("Provider")
    table.add_column("Version")
    table.add_column("Path")

    for name, agent in detected.items():
        style = f"agent.{name}" if name in ("claude", "gemini", "codex") else ""
        table.add_row(
            agent.display_name,
            agent.provider,
            agent.version,
            agent.binary_path,
            style=style,
        )

    console.print(table)
    console.print(f"\n  Primary orchestrator: [primary]{config.primary}[/primary]\n")
