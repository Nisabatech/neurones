"""Shared test fixtures for Neurones."""

from __future__ import annotations

import pytest

from neurones.adapters.claude import ClaudeAdapter
from neurones.adapters.codex import CodexAdapter
from neurones.adapters.detector import DetectedAgent
from neurones.adapters.gemini import GeminiAdapter
from neurones.models.config import AgentConfig, AppConfig
from neurones.models.result import AgentResult


@pytest.fixture
def sample_config():
    """Create a sample AppConfig for testing."""
    return AppConfig(
        primary="claude",
        parallel_timeout=60,
        json_output=True,
        agents={
            "claude": AgentConfig(timeout=30, max_turns=5),
            "gemini": AgentConfig(timeout=30),
            "codex": AgentConfig(timeout=30),
        },
    )


@pytest.fixture
def detected_agents():
    """Create mock detected agents."""
    return {
        "claude": DetectedAgent(
            name="claude",
            binary_path="/usr/local/bin/claude",
            version="2.1.0",
            display_name="Claude Code",
            provider="Anthropic",
        ),
        "gemini": DetectedAgent(
            name="gemini",
            binary_path="/usr/local/bin/gemini",
            version="0.25.0",
            display_name="Gemini CLI",
            provider="Google",
        ),
        "codex": DetectedAgent(
            name="codex",
            binary_path="/usr/local/bin/codex",
            version="0.98.0",
            display_name="Codex CLI",
            provider="OpenAI",
        ),
    }


@pytest.fixture
def mock_adapters():
    """Create adapter instances with fake binary paths."""
    return {
        "claude": ClaudeAdapter(binary_path="/usr/local/bin/claude", timeout=30),
        "gemini": GeminiAdapter(binary_path="/usr/local/bin/gemini", timeout=30),
        "codex": CodexAdapter(binary_path="/usr/local/bin/codex", timeout=30),
    }


@pytest.fixture
def success_result():
    """Create a successful AgentResult."""
    return AgentResult(
        agent_name="claude",
        output="Hello, world!",
        success=True,
        returncode=0,
        duration_seconds=1.5,
    )


@pytest.fixture
def failed_result():
    """Create a failed AgentResult."""
    return AgentResult(
        agent_name="gemini",
        output="",
        success=False,
        returncode=1,
        stderr="Connection refused",
        duration_seconds=0.5,
    )
