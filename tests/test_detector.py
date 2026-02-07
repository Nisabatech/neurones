"""Tests for agent detection."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from neurones.adapters.detector import AgentDetector, DetectedAgent


class TestAgentDetector:
    """Tests for AgentDetector."""

    def test_known_agents_defined(self):
        """All three agents are in KNOWN_AGENTS."""
        detector = AgentDetector()
        assert "claude" in detector.KNOWN_AGENTS
        assert "gemini" in detector.KNOWN_AGENTS
        assert "codex" in detector.KNOWN_AGENTS

    def test_known_agents_have_required_fields(self):
        """Each known agent entry has all required fields."""
        detector = AgentDetector()
        required = {"binary", "version_cmd", "version_pattern", "display_name", "provider"}
        for name, info in detector.KNOWN_AGENTS.items():
            assert required.issubset(info.keys()), f"{name} missing fields: {required - info.keys()}"

    @pytest.mark.asyncio
    async def test_detect_all_with_no_agents(self):
        """Returns empty dict when no agents found on PATH."""
        detector = AgentDetector()
        with patch("neurones.adapters.detector.shutil.which", return_value=None):
            result = await detector.detect_all()
        assert result == {}

    @pytest.mark.asyncio
    async def test_detect_all_with_agent_found(self):
        """Returns detected agent when binary found."""
        detector = AgentDetector()

        def mock_which(binary):
            return "/usr/bin/claude" if binary == "claude" else None

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"claude v1.2.3", b""))

        with (
            patch("neurones.adapters.detector.shutil.which", side_effect=mock_which),
            patch("neurones.adapters.detector.asyncio.create_subprocess_exec", return_value=mock_proc),
        ):
            result = await detector.detect_all()

        assert "claude" in result
        assert result["claude"].binary_path == "/usr/bin/claude"
        assert result["claude"].version == "1.2.3"
        assert result["claude"].display_name == "Claude Code"

    @pytest.mark.asyncio
    async def test_version_extraction_unknown(self):
        """Returns 'unknown' when version pattern doesn't match."""
        detector = AgentDetector()
        info = {"version_cmd": ["test", "--version"], "version_pattern": r"(\d+\.\d+\.\d+)"}

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"no version here", b""))

        with patch("neurones.adapters.detector.asyncio.create_subprocess_exec", return_value=mock_proc):
            version = await detector._get_version(info)

        assert version == "unknown"


class TestDetectedAgent:
    """Tests for DetectedAgent dataclass."""

    def test_creation(self):
        agent = DetectedAgent(
            name="claude",
            binary_path="/usr/bin/claude",
            version="1.0.0",
            display_name="Claude Code",
            provider="Anthropic",
        )
        assert agent.name == "claude"
        assert agent.available is True
