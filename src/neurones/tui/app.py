"""Main Textual App class for Neurones TUI dashboard."""

from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Header

from neurones import __version__
from neurones.adapters.claude import ClaudeAdapter
from neurones.adapters.codex import CodexAdapter
from neurones.adapters.detector import AgentDetector
from neurones.adapters.gemini import GeminiAdapter
from neurones.config import load_config
from neurones.core.executor import AgentExecutor
from neurones.core.orchestrator import Orchestrator
from neurones.logger import log
from neurones.tui.messages import ModeChanged, PromptSubmitted
from neurones.tui.widgets.agent_selector import AgentSelector
from neurones.tui.widgets.orchestration_view import OrchestrationView
from neurones.tui.widgets.prompt_input import PromptInput
from neurones.tui.widgets.status_bar import StatusBar

ADAPTER_CLASSES = {
    "claude": ClaudeAdapter,
    "gemini": GeminiAdapter,
    "codex": CodexAdapter,
}


class NeuronApp(App):
    """Neurones TUI Dashboard."""

    CSS_PATH = Path(__file__).parent / "styles" / "neurones.tcss"
    TITLE = f"Neurones v{__version__}"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+o", "switch_orchestrate", "Orchestrate Mode"),
        Binding("ctrl+r", "switch_direct", "Direct Run"),
        Binding("ctrl+e", "switch_compare", "Compare Mode"),
        Binding("ctrl+s", "open_settings", "Settings"),
        Binding("tab", "focus_next", "Next Panel"),
    ]

    current_mode: str = "orchestrate"

    def compose(self) -> ComposeResult:
        yield Header()
        yield StatusBar()
        yield PromptInput()
        with Horizontal(id="top-area"):
            yield AgentSelector()
            yield OrchestrationView()

    async def on_mount(self) -> None:
        """Initialize agents on app mount."""
        self.config_data = load_config()
        self._detected = {}
        self._adapters = {}
        self._executor = None
        self._orchestrator = None
        self._primary = self.config_data.primary

        # Focus the prompt input
        self.query_one(PromptInput).focus()

        # Detect agents
        await self._detect_agents()

    async def _detect_agents(self) -> None:
        """Detect installed agents and set up adapters."""
        detector = AgentDetector()
        self._detected = await detector.detect_all()
        log.info("Detected agents: %s", list(self._detected.keys()))

        # Build adapters
        for name, agent in self._detected.items():
            cls = ADAPTER_CLASSES.get(name)
            if cls:
                agent_cfg = self.config_data.get_agent_config(name)
                self._adapters[name] = cls(
                    binary_path=agent_cfg.binary_path or agent.binary_path,
                    timeout=agent_cfg.timeout,
                    auto_approve=agent_cfg.auto_approve,
                    default_model=agent_cfg.default_model,
                    extra_args=agent_cfg.extra_args,
                )

        self._executor = AgentExecutor(self._adapters, config=self.config_data)

        self._primary = self.config_data.primary
        if self._primary not in self._adapters and self._adapters:
            self._primary = next(iter(self._adapters))

        self._orchestrator = Orchestrator(
            primary=self._primary,
            adapters=self._adapters,
            executor=self._executor,
            config=self.config_data,
            available_agents=list(self._adapters.keys()),
        )

        # Update UI widgets
        agents_info = {}
        for name, agent in self._detected.items():
            agents_info[name] = {
                "display_name": agent.display_name,
                "version": agent.version,
                "available": agent.available,
                "primary": name == self._primary,
            }

        try:
            self.query_one(OrchestrationView).set_adapters(self._adapters, self._primary)
            self.query_one(AgentSelector).set_agents(agents_info, self._primary)
            self.query_one(StatusBar).set_agents(agents_info)
        except Exception as e:
            log.error("Failed to update UI: %s", e)

    async def on_prompt_submitted(self, event: PromptSubmitted) -> None:
        """Handle prompt submission from input bar."""
        prompt = event.value
        if not prompt:
            return

        log.info("TUI prompt submitted (mode=%s): %s", self.current_mode, prompt[:80])

        if self.current_mode == "orchestrate":
            async def _do_orchestrate() -> None:
                await self._run_orchestrated(prompt)
            self.run_worker(_do_orchestrate, thread=False)
        elif self.current_mode == "compare":
            async def _do_compare() -> None:
                await self._run_comparison(prompt)
            self.run_worker(_do_compare, thread=False)
        else:
            primary = self._primary
            async def _do_direct() -> None:
                await self._run_direct(primary, prompt)
            self.run_worker(_do_direct, thread=False)

    async def _run_orchestrated(self, prompt: str) -> None:
        orch_view = self.query_one(OrchestrationView)
        if self._orchestrator:
            await orch_view.run_orchestrated(self._orchestrator, prompt)

    async def _run_comparison(self, prompt: str) -> None:
        orch_view = self.query_one(OrchestrationView)
        await orch_view.run_comparison(prompt)

    async def _run_direct(self, agent_name: str, prompt: str) -> None:
        orch_view = self.query_one(OrchestrationView)
        await orch_view.run_direct(agent_name, prompt)

    def on_mode_changed(self, event: ModeChanged) -> None:
        self.current_mode = event.mode
        try:
            self.query_one(StatusBar).mode = event.mode
        except Exception:
            pass

    def action_switch_orchestrate(self) -> None:
        self.current_mode = "orchestrate"
        self._update_mode("orchestrate")

    def action_switch_direct(self) -> None:
        self.current_mode = "direct"
        self._update_mode("direct")

    def action_switch_compare(self) -> None:
        self.current_mode = "compare"
        self._update_mode("compare")

    def _update_mode(self, mode: str) -> None:
        try:
            self.query_one(AgentSelector).mode = mode
            self.query_one(StatusBar).mode = mode
        except Exception:
            pass

    def action_open_settings(self) -> None:
        from neurones.tui.screens.settings import SettingsScreen
        self.push_screen(
            SettingsScreen(self.config_data, self._detected),
            self._on_settings_closed,
        )

    async def _on_settings_closed(self, saved: bool | None) -> None:
        if saved:
            self.config_data = load_config()
            await self._detect_agents()
