"""Auto-detect installed AI CLI tools."""

from __future__ import annotations

import asyncio
import re
import shutil
from dataclasses import dataclass

from neurones.logger import log


@dataclass
class DetectedAgent:
    """Information about a detected AI CLI agent."""

    name: str
    binary_path: str
    version: str
    display_name: str
    provider: str
    available: bool = True


class AgentDetector:
    """Auto-detect installed AI CLI tools via PATH."""

    KNOWN_AGENTS = {
        "claude": {
            "binary": "claude",
            "version_cmd": ["claude", "--version"],
            "version_pattern": r"(\d+\.\d+\.\d+)",
            "display_name": "Claude Code",
            "provider": "Anthropic",
        },
        "gemini": {
            "binary": "gemini",
            "version_cmd": ["gemini", "--version"],
            "version_pattern": r"(\d+\.\d+\.\d+)",
            "display_name": "Gemini CLI",
            "provider": "Google",
        },
        "codex": {
            "binary": "codex",
            "version_cmd": ["codex", "--version"],
            "version_pattern": r"(\d+\.\d+\.\d+)",
            "display_name": "Codex CLI",
            "provider": "OpenAI",
        },
    }

    async def detect_all(self) -> dict[str, DetectedAgent]:
        """Probe PATH for each known agent, return available ones."""
        results = {}
        tasks = []
        for name, info in self.KNOWN_AGENTS.items():
            path = shutil.which(info["binary"])
            if path:
                log.info("Found %s at %s", name, path)
                tasks.append(self._detect_one(name, path, info))
            else:
                log.debug("Agent %s not found on PATH", name)

        detected = await asyncio.gather(*tasks, return_exceptions=True)
        for agent in detected:
            if isinstance(agent, DetectedAgent):
                results[agent.name] = agent
            elif isinstance(agent, Exception):
                log.warning("Detection failed: %s", agent)

        return results

    async def _detect_one(self, name: str, path: str, info: dict) -> DetectedAgent:
        """Detect a single agent's version."""
        version = await self._get_version(info)
        return DetectedAgent(
            name=name,
            binary_path=path,
            version=version,
            display_name=info["display_name"],
            provider=info["provider"],
            available=True,
        )

    async def _get_version(self, info: dict) -> str:
        """Run version command and extract version string."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *info["version_cmd"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            output = (stdout or stderr or b"").decode("utf-8", errors="replace")
            match = re.search(info["version_pattern"], output)
            return match.group(1) if match else "unknown"
        except (asyncio.TimeoutError, OSError) as e:
            log.warning("Failed to get version: %s", e)
            return "unknown"
