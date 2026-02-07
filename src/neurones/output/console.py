"""Rich console singleton and theme for Neurones."""

from rich.console import Console
from rich.theme import Theme

NEURONES_THEME = Theme({
    "agent.claude": "bold blue",
    "agent.gemini": "bold green",
    "agent.codex": "bold magenta",
    "status.success": "bold green",
    "status.failed": "bold red",
    "status.rate_limited": "bold #ff8800",
    "status.timeout": "bold yellow",
    "status.running": "bold yellow",
    "status.idle": "dim",
    "header": "bold #e94560",
    "primary": "bold cyan",
    "prompt": "bold white",
})

console = Console(theme=NEURONES_THEME)
error_console = Console(stderr=True, theme=NEURONES_THEME)
