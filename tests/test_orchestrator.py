"""Tests for the orchestrator."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from neurones.core.orchestrator import ORCHESTRATION_SYSTEM_PROMPT, Orchestrator
from neurones.models.result import AgentResult


class TestOrchestrator:
    """Tests for the Orchestrator brain."""

    def test_orchestration_prompt_contains_agents(self):
        """System prompt mentions all three agents."""
        assert "claude" in ORCHESTRATION_SYSTEM_PROMPT
        assert "gemini" in ORCHESTRATION_SYSTEM_PROMPT
        assert "codex" in ORCHESTRATION_SYSTEM_PROMPT

    def test_build_synthesis_prompt(self, mock_adapters, sample_config):
        """Synthesis prompt includes original task and all results."""
        executor = AsyncMock()
        orch = Orchestrator(
            primary="claude",
            adapters=mock_adapters,
            executor=executor,
            config=sample_config,
        )

        results = [
            AgentResult(agent_name="claude", output="Claude output", success=True),
            AgentResult(agent_name="gemini", output="Gemini output", success=True),
            AgentResult(agent_name="codex", output="", success=False, stderr="error"),
        ]

        prompt = orch._build_synthesis_prompt("Build an app", results)

        assert "ORIGINAL TASK: Build an app" in prompt
        assert "CLAUDE [SUCCESS]" in prompt
        assert "Claude output" in prompt
        assert "GEMINI [SUCCESS]" in prompt
        assert "CODEX [FAILED]" in prompt
        assert "Synthesize" in prompt

    @pytest.mark.asyncio
    async def test_run_no_delegation(self, mock_adapters, sample_config):
        """Claude primary forces worker delegation when plan says no delegation."""
        executor = AsyncMock()
        plan_result = AgentResult(
            agent_name="claude",
            output=json.dumps({
                "delegate": False,
                "reasoning": "Simple task",
                "subtasks": [],
                "self_task": None,
            }),
            success=True,
        )
        worker_results = [
            AgentResult(agent_name="gemini", output="Research output", success=True),
            AgentResult(agent_name="codex", output="Code output", success=True),
        ]
        synthesis_result = AgentResult(
            agent_name="claude",
            output="Synthesized response",
            success=True,
        )
        executor.run_single = AsyncMock(side_effect=[plan_result, synthesis_result])
        executor.run_parallel = AsyncMock(return_value=worker_results)

        orch = Orchestrator(
            primary="claude",
            adapters=mock_adapters,
            executor=executor,
            config=sample_config,
        )

        output = await orch.run("Say hello")
        assert output == "Synthesized response"
        executor.run_parallel.assert_called_once_with(
            [("gemini", "Say hello"), ("codex", "Say hello")]
        )

    @pytest.mark.asyncio
    async def test_run_with_delegation(self, mock_adapters, sample_config):
        """When primary delegates, runs subtasks in parallel then synthesizes."""
        executor = AsyncMock()

        plan_result = AgentResult(
            agent_name="claude",
            output=json.dumps({
                "delegate": True,
                "reasoning": "Complex task",
                "subtasks": [
                    {"agent": "gemini", "prompt": "Research X", "priority": "high"},
                    {"agent": "codex", "prompt": "Build Y", "priority": "high"},
                ],
                "self_task": None,
            }),
            success=True,
        )
        parallel_results = [
            AgentResult(agent_name="gemini", output="Research results", success=True),
            AgentResult(agent_name="codex", output="Code output", success=True),
        ]
        synthesis_result = AgentResult(
            agent_name="claude",
            output="Synthesized answer",
            success=True,
        )

        executor.run_single = AsyncMock(side_effect=[plan_result, synthesis_result])
        executor.run_parallel = AsyncMock(return_value=parallel_results)

        orch = Orchestrator(
            primary="claude",
            adapters=mock_adapters,
            executor=executor,
            config=sample_config,
        )

        output = await orch.run("Complex multi-agent task")
        assert output == "Synthesized answer"
        executor.run_parallel.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_fallback_on_analysis_failure(self, mock_adapters, sample_config):
        """Claude primary falls back to worker broadcast if analysis JSON is invalid."""
        executor = AsyncMock()
        bad_plan = AgentResult(
            agent_name="claude",
            output="Not valid JSON at all!!!",
            success=True,
        )
        worker_results = [
            AgentResult(agent_name="gemini", output="Gemini fallback", success=True),
            AgentResult(agent_name="codex", output="Codex fallback", success=True),
        ]
        synthesis_result = AgentResult(
            agent_name="claude",
            output="Synthesized fallback response",
            success=True,
        )
        executor.run_single = AsyncMock(side_effect=[bad_plan, synthesis_result])
        executor.run_parallel = AsyncMock(return_value=worker_results)

        orch = Orchestrator(
            primary="claude",
            adapters=mock_adapters,
            executor=executor,
            config=sample_config,
        )

        output = await orch.run("Some prompt")
        assert output == "Synthesized fallback response"
        executor.run_parallel.assert_called_once_with(
            [("gemini", "Some prompt"), ("codex", "Some prompt")]
        )

    @pytest.mark.asyncio
    async def test_run_fallback_on_analysis_failure_non_claude_primary(self, mock_adapters, sample_config):
        """Non-Claude primary still falls back to direct execution on analysis failure."""
        executor = AsyncMock()
        bad_plan = AgentResult(
            agent_name="codex",
            output="Not valid JSON at all!!!",
            success=True,
        )
        fallback_result = AgentResult(
            agent_name="codex",
            output="Direct fallback response",
            success=True,
        )
        executor.run_single = AsyncMock(side_effect=[bad_plan, fallback_result])

        orch = Orchestrator(
            primary="codex",
            adapters=mock_adapters,
            executor=executor,
            config=sample_config,
        )

        output = await orch.run("Some prompt")
        assert output == "Direct fallback response"
        executor.run_parallel.assert_not_called()
