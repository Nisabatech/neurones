"""Default orchestration command — nr "prompt"."""

from __future__ import annotations

import asyncio

from neurones.adapters.claude import ClaudeAdapter
from neurones.adapters.codex import CodexAdapter
from neurones.adapters.detector import AgentDetector
from neurones.adapters.gemini import GeminiAdapter
from neurones.config import load_config
from neurones.core.executor import AgentExecutor
from neurones.core.orchestrator import Orchestrator
from neurones.exceptions import NoAgentsDetectedError
from neurones.output.console import console, error_console


ADAPTER_CLASSES = {
    "claude": ClaudeAdapter,
    "gemini": GeminiAdapter,
    "codex": CodexAdapter,
}


def _build_adapters(detected: dict, config) -> dict:
    """Build adapter instances from detected agents and config."""
    adapters = {}
    for name, agent in detected.items():
        cls = ADAPTER_CLASSES.get(name)
        if cls is None:
            continue
        agent_cfg = config.get_agent_config(name)
        adapters[name] = cls(
            binary_path=agent_cfg.binary_path or agent.binary_path,
            timeout=agent_cfg.timeout,
            auto_approve=agent_cfg.auto_approve,
            default_model=agent_cfg.default_model,
            extra_args=agent_cfg.extra_args,
        )
    return adapters


async def orchestrate(prompt: str) -> None:
    """Run the orchestration flow for a given prompt."""
    config = load_config()

    with console.status("[status.running]Detecting agents...[/status.running]"):
        detector = AgentDetector()
        detected = await detector.detect_all()

    if not detected:
        raise NoAgentsDetectedError()

    adapters = _build_adapters(detected, config)

    if config.primary not in adapters:
        # Fall back to first available agent as primary
        fallback = next(iter(adapters))
        error_console.print(
            f"[status.failed]Primary agent '{config.primary}' not available. "
            f"Falling back to '{fallback}'.[/status.failed]"
        )
        primary = fallback
    else:
        primary = config.primary

    executor = AgentExecutor(adapters, config=config)
    orchestrator = Orchestrator(
        primary=primary,
        adapters=adapters,
        executor=executor,
        config=config,
        available_agents=list(adapters.keys()),
    )

    console.print(f"\n[header]Neurones[/header] — Orchestrating with [primary]{primary}[/primary] as brain\n")

    with console.status("[status.running]Thinking...[/status.running]"):
        output = await orchestrator.run(prompt)

    console.print(output)
    console.print()
