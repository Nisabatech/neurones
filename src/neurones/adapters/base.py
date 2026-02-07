"""Abstract base class for agent adapters."""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from neurones.models.result import AgentResult

# Patterns that indicate rate limiting across various CLI tools
RATE_LIMIT_PATTERNS = [
    re.compile(r"rate.?limit", re.IGNORECASE),
    re.compile(r"too many requests", re.IGNORECASE),
    re.compile(r"429", re.IGNORECASE),
    re.compile(r"quota.?exceeded", re.IGNORECASE),
    re.compile(r"resource.?exhausted", re.IGNORECASE),
    re.compile(r"overloaded", re.IGNORECASE),
    re.compile(r"retry.?after", re.IGNORECASE),
    re.compile(r"tokens?.?per.?min", re.IGNORECASE),
    re.compile(r"requests?.?per.?min", re.IGNORECASE),
]

RETRY_AFTER_PATTERN = re.compile(r"retry.?after[:\s]+(\d+(?:\.\d+)?)", re.IGNORECASE)


class AgentAdapter(ABC):
    """Abstract interface for AI CLI agent adapters."""

    name: str
    display_name: str
    provider: str

    def __init__(self, binary_path: str, timeout: int = 300, auto_approve: bool = True,
                 default_model: str | None = None, extra_args: list[str] | None = None):
        self.binary_path = binary_path
        self.timeout = timeout
        self.auto_approve = auto_approve
        self.default_model = default_model
        self.extra_args = extra_args or []

    @abstractmethod
    def build_command(self, prompt: str, *, json_output: bool = False,
                      model: str | None = None, auto_approve: bool | None = None,
                      system_prompt: str | None = None, max_turns: int | None = None) -> list[str]:
        """Build the CLI command list for this agent."""

    def parse_output(self, stdout: bytes, stderr: bytes, returncode: int) -> AgentResult:
        """Parse subprocess output into an AgentResult."""
        output = stdout.decode("utf-8", errors="replace").strip()
        err = self._filter_stderr(stderr.decode("utf-8", errors="replace").strip())

        rate_limited = self.is_rate_limited(output, err, returncode)

        return AgentResult(
            agent_name=self.name,
            output=output,
            success=returncode == 0 and not rate_limited,
            returncode=returncode,
            stderr=err,
            rate_limited=rate_limited,
        )

    def is_rate_limited(self, stdout: str, stderr: str, returncode: int) -> bool:
        """Check if the output indicates a rate limit error."""
        combined = f"{stdout}\n{stderr}"
        return any(p.search(combined) for p in RATE_LIMIT_PATTERNS)

    def extract_retry_after(self, stdout: str, stderr: str) -> float | None:
        """Try to extract a retry-after delay in seconds from the output."""
        combined = f"{stdout}\n{stderr}"
        match = RETRY_AFTER_PATTERN.search(combined)
        if match:
            return float(match.group(1))
        return None

    def _filter_stderr(self, stderr: str) -> str:
        """Override in subclasses to filter known benign warnings."""
        return stderr

    async def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        """Stream agent output line-by-line."""
        cmd = self.build_command(prompt, **kwargs)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert proc.stdout is not None
        async for line in proc.stdout:
            yield line.decode("utf-8", errors="replace")
        await proc.wait()
