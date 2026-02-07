"""Side-by-side comparison of multiple agent results."""

from __future__ import annotations

from neurones.core.executor import AgentExecutor
from neurones.logger import log
from neurones.models.result import AgentResult


class Comparator:
    """Run the same prompt on all agents and compare results side-by-side."""

    def __init__(self, adapters: dict, executor: AgentExecutor):
        self.adapters = adapters
        self.executor = executor

    async def compare(self, prompt: str, agents: list[str] | None = None) -> list[AgentResult]:
        """Run prompt on specified agents (or all) in parallel."""
        target_agents = agents or list(self.adapters.keys())
        tasks = [(agent, prompt) for agent in target_agents if agent in self.adapters]

        if not tasks:
            log.warning("No agents available for comparison")
            return []

        log.info("Comparing across %d agents: %s", len(tasks), [t[0] for t in tasks])
        results = await self.executor.run_parallel(tasks)
        return results
