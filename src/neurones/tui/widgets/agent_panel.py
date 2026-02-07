"""Per-agent live output panel widget."""

from __future__ import annotations

from typing import Any

from textual.reactive import reactive
from textual.widgets import RichLog

from neurones.adapters.base import AgentAdapter
from neurones.core.utils import clean_ansi


class AgentPanel(RichLog):
    """Live output panel for a single agent."""

    status: reactive[str] = reactive("idle")

    BORDER_COLORS = {
        "idle": "grey",
        "running": "yellow",
        "success": "green",
        "failed": "red",
        "timeout": "red",
        "rate_limited": "#ff8800",
    }

    def __init__(self, agent_name: str, display_name: str, **kwargs: Any) -> None:
        super().__init__(highlight=True, markup=True, wrap=True, id=f"panel-{agent_name}", **kwargs)
        self.agent_name = agent_name
        self.display_name = display_name
        self.border_title = display_name

    def watch_status(self, old_value: str, new_value: str) -> None:
        """Update border color based on status."""
        color = self.BORDER_COLORS.get(new_value, "grey")
        self.styles.border = ("round", color)

        # Update CSS class
        self.remove_class(old_value)
        self.add_class(new_value)

    async def stream_output(self, adapter: AgentAdapter, prompt: str, **kwargs: Any) -> None:
        """Stream agent output line by line into the panel."""
        self.status = "running"
        self.clear()
        try:
            async for chunk in adapter.stream(prompt, **kwargs):
                cleaned = clean_ansi(chunk)
                if cleaned.strip():
                    self.write(cleaned.rstrip())
            self.status = "success"
        except Exception as e:
            self.write(f"\n[red]Error: {e}[/red]")
            self.status = "failed"

    def reset(self) -> None:
        """Reset panel to idle state."""
        self.clear()
        self.status = "idle"
        self.border_title = self.display_name
