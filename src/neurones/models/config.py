"""Pydantic configuration models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    binary_path: str | None = None  # Auto-detected if omitted
    default_model: str | None = None
    auto_approve: bool = True
    timeout: int = 300
    max_turns: int | None = None
    extra_args: list[str] = Field(default_factory=list)


class AppConfig(BaseModel):
    """Top-level application configuration."""

    primary: str = "claude"
    parallel_timeout: int = 600
    json_output: bool = True
    max_retries: int = 3
    retry_base_delay: float = 5.0
    retry_max_delay: float = 60.0
    agents: dict[str, AgentConfig] = Field(default_factory=lambda: {
        "claude": AgentConfig(auto_approve=True, max_turns=15),
        "gemini": AgentConfig(auto_approve=True),
        "codex": AgentConfig(auto_approve=True, extra_args=["--skip-git-repo-check"]),
    })

    def get_agent_config(self, name: str) -> AgentConfig:
        """Get config for a specific agent, with defaults."""
        return self.agents.get(name, AgentConfig())
