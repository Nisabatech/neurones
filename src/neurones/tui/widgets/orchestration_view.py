"""Orchestration flow visualization container."""

from __future__ import annotations

import asyncio
from typing import Any

from textual.containers import Vertical
from neurones.adapters.base import AgentAdapter
from neurones.core.orchestrator import Orchestrator
from neurones.tui.widgets.agent_panel import AgentPanel


# Default panels — created at compose time, updated when agents detected
DEFAULT_PANELS = [
    ("claude", "Claude Code (Primary)"),
    ("gemini", "Gemini CLI"),
    ("codex", "Codex CLI"),
]


class OrchestrationView(Vertical):
    """Shows the orchestration flow: analyze -> dispatch -> collect -> synthesize."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(id="main-area", **kwargs)
        self._adapters: dict[str, AgentAdapter] = {}

    def compose(self):
        """Create all three agent panels upfront."""
        for name, display in DEFAULT_PANELS:
            yield AgentPanel(name, display)

    def set_adapters(self, adapters: dict[str, AgentAdapter], primary: str) -> None:
        """Store adapters and update panel titles based on detection."""
        self._adapters = adapters
        for name, display in DEFAULT_PANELS:
            try:
                panel = self.query_one(f"#panel-{name}", AgentPanel)
                if name not in adapters:
                    panel.border_title = f"{display} (not installed)"
                elif name == primary:
                    panel.border_title = f"{display} (Primary)"
                else:
                    panel.border_title = display
            except Exception:
                pass

    def _get_panel(self, agent_name: str) -> AgentPanel | None:
        """Get panel by agent name."""
        try:
            return self.query_one(f"#panel-{agent_name}", AgentPanel)
        except Exception:
            return None

    def reset_all(self) -> None:
        """Reset all panels to idle."""
        for name, _ in DEFAULT_PANELS:
            panel = self._get_panel(name)
            if panel:
                panel.reset()

    async def run_orchestrated(self, orchestrator: Orchestrator, prompt: str) -> None:
        """Run orchestration with live panel updates."""
        self.reset_all()

        primary_panel = self._get_panel(orchestrator.primary)
        if not primary_panel:
            return

        # Step 1: Show analysis phase
        primary_panel.status = "running"
        primary_panel.write("[bold]Analyzing task...[/bold]\n")
        coordinator_only = orchestrator._primary_is_coordinator_only()

        def build_worker_subtasks() -> list[dict[str, str]]:
            return [
                {"agent": name, "prompt": prompt}
                for name in self._adapters
                if name != orchestrator.primary
            ]

        try:
            plan = await orchestrator._analyze(prompt)
        except Exception as e:
            if coordinator_only:
                primary_panel.write(
                    "[yellow]Analysis failed; primary is coordinator-only, "
                    "broadcasting to worker agents.[/yellow]\n"
                )
                plan = {
                    "delegate": True,
                    "reasoning": str(e),
                    "subtasks": build_worker_subtasks(),
                    "self_task": None,
                }
            else:
                primary_panel.write(f"[yellow]Analysis failed, running directly: {e}[/yellow]\n")
                adapter = self._adapters.get(orchestrator.primary)
                if adapter:
                    await primary_panel.stream_output(adapter, prompt)
                return

        if not plan.get("delegate", False):
            if coordinator_only:
                primary_panel.write(
                    "[dim]Primary is coordinator-only; forcing worker delegation.[/dim]\n\n"
                )
                plan["subtasks"] = build_worker_subtasks()
            else:
                primary_panel.write("[dim]Handling directly (no delegation needed)[/dim]\n\n")
                adapter = self._adapters.get(orchestrator.primary)
                if adapter:
                    await primary_panel.stream_output(adapter, prompt)
                return

        # Step 2: Show delegation plan
        reasoning = plan.get("reasoning", "")
        if reasoning:
            primary_panel.write(f"[dim]{reasoning}[/dim]\n")

        subtasks = plan.get("subtasks", [])
        valid_subtasks = []
        for subtask in subtasks:
            agent = subtask.get("agent", "")
            task_prompt = subtask.get("prompt", "")
            if not isinstance(task_prompt, str) or not task_prompt.strip():
                continue
            if agent not in self._adapters:
                continue
            if coordinator_only and agent == orchestrator.primary:
                continue
            valid_subtasks.append({"agent": agent, "prompt": task_prompt})
            panel = self._get_panel(agent)
            if panel:
                panel.write(f"[bold]Assigned:[/bold] {task_prompt[:100]}...\n\n")
                primary_panel.write(
                    f"[bold]Delegating to {agent}:[/bold] \"{task_prompt[:60]}...\"\n"
                )

        if not valid_subtasks and coordinator_only:
            valid_subtasks = build_worker_subtasks()
            for subtask in valid_subtasks:
                agent = subtask["agent"]
                task_prompt = subtask["prompt"]
                panel = self._get_panel(agent)
                if panel:
                    panel.write(f"[bold]Assigned:[/bold] {task_prompt[:100]}...\n\n")
                    primary_panel.write(
                        f"[bold]Delegating to {agent}:[/bold] \"{task_prompt[:60]}...\"\n"
                    )

        # Step 3: Run all panels in parallel
        stream_tasks = []
        for subtask in valid_subtasks:
            agent = subtask.get("agent", "")
            task_prompt = subtask.get("prompt", "")
            panel = self._get_panel(agent)
            adapter = self._adapters.get(agent)
            if panel and adapter:
                stream_tasks.append(panel.stream_output(adapter, task_prompt))

        # Also run primary self-task if present
        self_task = plan.get("self_task")
        if (
            self_task
            and (not coordinator_only)
            and orchestrator.primary in self._adapters
        ):
            primary_panel.write(f"\n[bold]Self-task:[/bold] {self_task[:80]}...\n\n")
            stream_tasks.append(
                primary_panel.stream_output(
                    self._adapters[orchestrator.primary], self_task
                )
            )
        elif self_task and coordinator_only:
            primary_panel.write(
                "[dim]Skipping self-task (primary is coordinator-only).[/dim]\n"
            )

        if stream_tasks:
            await asyncio.gather(*stream_tasks, return_exceptions=True)
        elif coordinator_only:
            primary_panel.write(
                "[yellow]No worker agent available for coordinator-only primary.[/yellow]\n"
            )

        # Step 4: Synthesis
        primary_panel.write("\n[bold]Synthesizing results...[/bold]\n")

    async def run_direct(self, agent_name: str, prompt: str) -> None:
        """Run a prompt directly on one agent."""
        self.reset_all()
        panel = self._get_panel(agent_name)
        adapter = self._adapters.get(agent_name)
        if panel and adapter:
            await panel.stream_output(adapter, prompt)

    async def run_comparison(self, prompt: str) -> None:
        """Run prompt on all agents in parallel."""
        self.reset_all()
        tasks = []
        for name, _ in DEFAULT_PANELS:
            panel = self._get_panel(name)
            adapter = self._adapters.get(name)
            if panel and adapter:
                tasks.append(panel.stream_output(adapter, prompt))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
