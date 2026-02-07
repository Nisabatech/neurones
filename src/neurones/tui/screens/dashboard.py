"""Main dashboard screen for Neurones TUI."""

from __future__ import annotations

from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Header

from neurones.tui.widgets.agent_panel import AgentPanel
from neurones.tui.widgets.agent_selector import AgentSelector
from neurones.tui.widgets.orchestration_view import OrchestrationView
from neurones.tui.widgets.prompt_input import PromptInput
from neurones.tui.widgets.status_bar import StatusBar


class DashboardScreen(Screen):
    """Main dashboard screen layout."""

    def compose(self):
        yield Header()
        with Horizontal():
            yield AgentSelector()
            yield OrchestrationView()
        yield PromptInput()
        yield StatusBar()
