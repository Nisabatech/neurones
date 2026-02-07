"""Parallel comparison command — nr compare "prompt"."""

from __future__ import annotations

import asyncio

import click

from neurones.output.console import console


@click.command()
@click.argument("prompt")
@click.option("--agents", "-a", default=None, help="Comma-separated agent names (default: all)")
def compare(prompt: str, agents: str | None) -> None:
    """Run a prompt on all agents in parallel and compare results.

    Example: nr compare "Write a merge sort in Python"
    """
    agent_list = agents.split(",") if agents else None
    asyncio.run(_compare(prompt, agent_list))


async def _compare(prompt: str, agents: list[str] | None) -> None:
    """Execute comparison across agents."""
    from neurones.adapters.detector import AgentDetector
    from neurones.cli.orchestrate_cmd import _build_adapters
    from neurones.config import load_config
    from neurones.core.comparator import Comparator
    from neurones.core.executor import AgentExecutor
    from neurones.output.formatters import format_comparison_table

    config = load_config()

    with console.status("[status.running]Detecting agents...[/status.running]"):
        detector = AgentDetector()
        detected = await detector.detect_all()

    if not detected:
        console.print("[status.failed]No agents detected.[/status.failed]")
        raise SystemExit(1)

    adapters = _build_adapters(detected, config)
    executor = AgentExecutor(adapters)
    comparator = Comparator(adapters, executor)

    agent_names = agents or list(adapters.keys())
    console.print(f"\n[header]Neurones[/header] — Comparing across: {', '.join(agent_names)}\n")

    with console.status("[status.running]Running all agents in parallel...[/status.running]"):
        results = await comparator.compare(prompt, agents)

    format_comparison_table(results, console)
    console.print()
