"""Settings/config screen for Neurones TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static


class SettingsScreen(ModalScreen):
    """Settings configuration screen."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
    ]

    def __init__(self, config, detected_agents: dict) -> None:
        super().__init__()
        self._config = config
        self._detected = detected_agents

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-container"):
            yield Label("[bold]Settings[/bold]", classes="label")
            yield Static("")

            yield Label("Primary Agent:")
            agent_options = [(name, name) for name in self._detected]
            yield Select(
                options=agent_options,
                value=self._config.primary,
                id="select-primary",
            )

            yield Static("")
            yield Label("Parallel Timeout (seconds):")
            yield Input(
                str(self._config.parallel_timeout),
                id="input-timeout",
                type="integer",
            )

            yield Static("")
            for name in self._detected:
                agent_cfg = self._config.get_agent_config(name)
                yield Label(f"[bold]{name.title()}[/bold] timeout:")
                yield Input(
                    str(agent_cfg.timeout),
                    id=f"input-{name}-timeout",
                    type="integer",
                )

            yield Static("")
            yield Button("Save", variant="primary", id="btn-save")
            yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle save/cancel."""
        if event.button.id == "btn-save":
            self._save()
            self.dismiss(True)
        elif event.button.id == "btn-cancel":
            self.dismiss(False)

    def _save(self) -> None:
        """Save settings to config."""
        from neurones.config import save_config

        select = self.query_one("#select-primary", Select)
        if select.value is not None:
            self._config.primary = str(select.value)

        timeout_input = self.query_one("#input-timeout", Input)
        try:
            self._config.parallel_timeout = int(timeout_input.value)
        except ValueError:
            pass

        for name in self._detected:
            agent_input = self.query_one(f"#input-{name}-timeout", Input)
            try:
                agent_cfg = self._config.get_agent_config(name)
                agent_cfg.timeout = int(agent_input.value)
                self._config.agents[name] = agent_cfg
            except ValueError:
                pass

        save_config(self._config)
