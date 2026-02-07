"""TOML configuration loading from ~/.neurones/config.toml."""

from __future__ import annotations

from pathlib import Path

import toml

from neurones.logger import log
from neurones.models.config import AgentConfig, AppConfig

CONFIG_DIR = Path.home() / ".neurones"
CONFIG_FILE = CONFIG_DIR / "config.toml"

_DEFAULT_CONFIG_TOML = """\
# Neurones configuration
# Primary orchestrator agent (brain)
primary = "claude"

# Global settings
parallel_timeout = 600
json_output = true

# Rate limit retry settings
max_retries = 3
retry_base_delay = 5.0
retry_max_delay = 60.0

[agents.claude]
auto_approve = true
timeout = 300
max_turns = 15

[agents.gemini]
auto_approve = true
timeout = 300

[agents.codex]
auto_approve = true
timeout = 300
extra_args = ["--skip-git-repo-check"]
"""


def load_config() -> AppConfig:
    """Load configuration from ~/.neurones/config.toml, creating defaults if missing."""
    if not CONFIG_FILE.exists():
        log.info("No config file found, creating default at %s", CONFIG_FILE)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(_DEFAULT_CONFIG_TOML, encoding="utf-8")
        return AppConfig()

    try:
        raw = toml.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        log.debug("Loaded config: %s", raw)
        return _parse_raw_config(raw)
    except Exception as e:
        log.warning("Failed to parse config, using defaults: %s", e)
        return AppConfig()


def _parse_raw_config(raw: dict) -> AppConfig:
    """Parse raw TOML dict into AppConfig."""
    agents = {}
    for name, agent_raw in raw.get("agents", {}).items():
        agents[name] = AgentConfig(**agent_raw)

    return AppConfig(
        primary=raw.get("primary", "claude"),
        parallel_timeout=raw.get("parallel_timeout", 600),
        json_output=raw.get("json_output", True),
        max_retries=raw.get("max_retries", 3),
        retry_base_delay=raw.get("retry_base_delay", 5.0),
        retry_max_delay=raw.get("retry_max_delay", 60.0),
        agents=agents if agents else AppConfig().agents,
    )


def save_config(config: AppConfig) -> None:
    """Save configuration back to ~/.neurones/config.toml."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    data: dict = {
        "primary": config.primary,
        "parallel_timeout": config.parallel_timeout,
        "json_output": config.json_output,
        "max_retries": config.max_retries,
        "retry_base_delay": config.retry_base_delay,
        "retry_max_delay": config.retry_max_delay,
        "agents": {},
    }
    for name, agent_cfg in config.agents.items():
        agent_dict = agent_cfg.model_dump(exclude_none=True, exclude_defaults=False)
        # Remove empty extra_args to keep config clean
        if not agent_dict.get("extra_args"):
            agent_dict.pop("extra_args", None)
        data["agents"][name] = agent_dict

    CONFIG_FILE.write_text(toml.dumps(data), encoding="utf-8")
    log.info("Saved config to %s", CONFIG_FILE)
