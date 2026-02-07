"""Direct agent run command — nr run <agent> "prompt"."""

from __future__ import annotations

import asyncio

import click

from neurones.output.console import console, error_console


@click.command()
@click.argument("agent")
@click.argument("prompt")
def run(agent: str, prompt: str) -> None:
    """Run a prompt directly on a specific agent.

    Example: nr run claude "Explain this architecture"
    """
    asyncio.run(_run_direct(agent, prompt))


async def _run_direct(agent_name: str, prompt: str) -> None:
    """Execute a prompt directly on the specified agent."""
    from neurones.adapters.detector import AgentDetector
    from neurones.cli.orchestrate_cmd import _build_adapters
    from neurones.config import load_config
    from neurones.core.executor import AgentExecutor

    config = load_config()

    with console.status(f"[status.running]Detecting {agent_name}...[/status.running]"):
        detector = AgentDetector()
        detected = await detector.detect_all()

    if agent_name not in detected:
        error_console.print(
            f"[status.failed]Agent '{agent_name}' not found. "
            f"Available: {', '.join(detected.keys()) or 'none'}[/status.failed]"
        )
        raise SystemExit(1)

    adapters = _build_adapters(detected, config)
    executor = AgentExecutor(adapters)

    console.print(f"\n[agent.{agent_name}]{detected[agent_name].display_name}[/agent.{agent_name}]\n")

    with console.status(f"[status.running]Running on {agent_name}...[/status.running]"):
        result = await executor.run_single(agent_name, prompt)

    if result.success:
        console.print(result.output)
    else:
        error_console.print(f"[status.failed]{result.stderr}[/status.failed]")
        raise SystemExit(1)

    console.print(f"\n[dim]Completed in {result.duration_seconds:.1f}s[/dim]\n")
