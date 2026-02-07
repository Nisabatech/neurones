"""Bottom status bar showing agent status, mode, and keybindings."""

from __future__ import annotations

from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class StatusBar(Static):
    """Shows agent status dots, current mode, and keyboard shortcuts."""

    mode: reactive[str] = reactive("orchestrate")
    agent_statuses: reactive[dict] = reactive({}, layout=True)

    def __init__(self) -> None:
        super().__init__(id="status-bar")
        self._agents: dict[str, dict] = {}

    def set_agents(self, agents: dict) -> None:
        """Set the detected agents info."""
        self._agents = agents
        self._update_display()

    def watch_mode(self, old_value: str, new_value: str) -> None:
        """Update display when mode changes."""
        self._update_display()

    def watch_agent_statuses(self, old_value: dict, new_value: dict) -> None:
        """Update display when agent statuses change."""
        self._update_display()

    def _update_display(self) -> None:
        """Rebuild the status bar text."""
        parts = []

        for name, info in self._agents.items():
            status = self.agent_statuses.get(name, "idle")
            dot_color = {"idle": "grey", "running": "yellow", "success": "green", "failed": "red"}.get(status, "grey")
            primary_mark = " (primary)" if info.get("primary") else ""
            version = info.get("version", "")
            version_str = f" v{version}" if version and version != "unknown" else ""
            parts.append(f"[{dot_color}]●[/{dot_color}] {name}{version_str}{primary_mark}")

        agent_str = " | ".join(parts) if parts else "No agents detected"

        mode_map = {"orchestrate": "Orchestrate", "direct": "Direct", "compare": "Compare"}
        mode_label = mode_map.get(self.mode, self.mode.title())

        self.update(f" {agent_str} | Mode: [bold #e94560]{mode_label}[/bold #e94560] | Ctrl+Q quit")
