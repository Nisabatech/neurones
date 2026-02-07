"""Prompt input bar with history support."""

from __future__ import annotations

from textual.widgets import Input

from neurones.tui.messages import PromptSubmitted


class PromptInput(Input):
    """Bottom prompt input with history support."""

    def __init__(self) -> None:
        super().__init__(
            placeholder="Enter your prompt... (Ctrl+O: Orchestrate, Ctrl+R: Direct, Ctrl+C: Compare)",
            id="prompt-input",
        )
        self.history: list[str] = []
        self.history_index: int = -1

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key — post prompt and add to history."""
        value = event.value.strip()
        if not value:
            return

        self.history.insert(0, value)
        self.history_index = -1
        self.value = ""

        self.post_message(PromptSubmitted(value))

    def on_key(self, event) -> None:
        """Handle up/down arrow keys for history navigation."""
        if event.key == "up" and self.history:
            self.history_index = min(self.history_index + 1, len(self.history) - 1)
            self.value = self.history[self.history_index]
            event.prevent_default()
        elif event.key == "down" and self.history:
            self.history_index = max(self.history_index - 1, -1)
            self.value = self.history[self.history_index] if self.history_index >= 0 else ""
            event.prevent_default()
