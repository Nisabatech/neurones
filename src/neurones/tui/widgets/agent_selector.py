"""Agent selection sidebar widget."""

from __future__ import annotations

from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Button, Label, Static

from neurones.tui.messages import ModeChanged

MODE_LABELS = {
    "orchestrate": "Orchestrate",
    "direct": "Direct",
    "compare": "Compare",
}


class AgentSelector(Vertical):
    """Left sidebar showing agents and mode controls."""

    mode: reactive[str] = reactive("orchestrate")

    def __init__(self) -> None:
        super().__init__(id="sidebar")
        self._agents: dict = {}
        self._primary: str = ""

    def compose(self):
        yield Label("[bold]Agents[/bold]", classes="label")
        yield Static("Detecting...", id="agent-list")
        yield Static("")
        yield Label("[bold]Mode[/bold]", classes="label")
        yield Static(MODE_LABELS.get(self.mode, self.mode), id="mode-display")
        yield Static("")
        yield Button("Orchestrate", id="btn-orchestrate", variant="primary")
        yield Button("Direct", id="btn-direct")
        yield Button("Compare", id="btn-compare")

    def set_agents(self, agents: dict, primary: str) -> None:
        """Update the detected agents display."""
        self._agents = agents
        self._primary = primary
        self._update_agent_list()

    def _update_agent_list(self) -> None:
        """Update just the agent list text."""
        lines = []
        for name, info in self._agents.items():
            dot = "[green]●[/green]" if info.get("available") else "[red]●[/red]"
            primary_mark = " (Primary)" if name == self._primary else ""
            lines.append(f" {dot} {info.get('display_name', name)}{primary_mark}")

        try:
            agent_list = self.query_one("#agent-list", Static)
            agent_list.update("\n".join(lines) if lines else "No agents")
        except Exception:
            pass

    def _update_mode_display(self) -> None:
        """Update just the mode label."""
        try:
            mode_display = self.query_one("#mode-display", Static)
            mode_display.update(f" {MODE_LABELS.get(self.mode, self.mode)}")
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle mode button clicks."""
        mode_map = {
            "btn-orchestrate": "orchestrate",
            "btn-direct": "direct",
            "btn-compare": "compare",
        }
        new_mode = mode_map.get(event.button.id or "")
        if new_mode and new_mode != self.mode:
            self.mode = new_mode
            self.post_message(ModeChanged(new_mode))

    def watch_mode(self, old_value: str, new_value: str) -> None:
        """Update mode label when mode changes."""
        self._update_mode_display()
