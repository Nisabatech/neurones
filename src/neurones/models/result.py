"""Agent execution result model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """Result of a single agent execution."""

    agent_name: str
    output: str
    success: bool
    returncode: int = 0
    stderr: str = ""
    duration_seconds: float = 0.0
    rate_limited: bool = False
    retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_error(cls, agent_name: str, error: Exception) -> AgentResult:
        """Create a failed result from an exception."""
        return cls(
            agent_name=agent_name,
            output="",
            success=False,
            returncode=-1,
            stderr=str(error),
        )

    @property
    def status_label(self) -> str:
        """Human-readable status."""
        if self.success:
            if self.retries > 0:
                return f"SUCCESS (retried {self.retries}x)"
            return "SUCCESS"
        if self.rate_limited:
            return "RATE_LIMITED"
        if "timed out" in self.stderr.lower() or "timeout" in self.stderr.lower():
            return "TIMEOUT"
        return "FAILED"

    @property
    def truncated_output(self) -> str:
        """First 500 chars of output for summaries."""
        if len(self.output) <= 500:
            return self.output
        return self.output[:500] + "..."
