"""Tests for the async executor."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from neurones.adapters.claude import ClaudeAdapter
from neurones.core.executor import AgentExecutor
from neurones.models.config import AppConfig
from neurones.models.result import AgentResult


@pytest.fixture
def fast_retry_config():
    """Config with fast retries for testing."""
    return AppConfig(max_retries=2, retry_base_delay=0.01, retry_max_delay=0.05)


class TestAgentExecutor:
    """Tests for AgentExecutor."""

    def test_unknown_agent_returns_error(self):
        """run_single returns error for unknown agent."""
        executor = AgentExecutor(adapters={})

        import asyncio
        result = asyncio.run(executor.run_single("nonexistent", "test"))

        assert not result.success
        assert "Unknown agent" in result.stderr

    @pytest.mark.asyncio
    async def test_run_single_success(self):
        """Successful subprocess execution returns proper result."""
        adapter = ClaudeAdapter(binary_path="/usr/bin/claude", timeout=30)

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"Hello!", b""))
        mock_proc.returncode = 0

        executor = AgentExecutor(adapters={"claude": adapter})

        with patch("neurones.core.executor.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.run_single("claude", "Say hello")

        assert result.success
        assert result.output == "Hello!"
        assert result.agent_name == "claude"
        assert result.duration_seconds > 0
        assert result.retries == 0
        assert not result.rate_limited

    @pytest.mark.asyncio
    async def test_run_single_failure(self):
        """Failed subprocess returns error result."""
        adapter = ClaudeAdapter(binary_path="/usr/bin/claude", timeout=30)

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"Error occurred"))
        mock_proc.returncode = 1

        executor = AgentExecutor(adapters={"claude": adapter})

        with patch("neurones.core.executor.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.run_single("claude", "bad prompt")

        assert not result.success
        assert result.returncode == 1

    @pytest.mark.asyncio
    async def test_run_single_rate_limit_retries(self, fast_retry_config):
        """Rate-limited response triggers retries."""
        adapter = ClaudeAdapter(binary_path="/usr/bin/claude", timeout=30)

        # First two calls rate-limited, third succeeds
        rate_limited_proc = AsyncMock()
        rate_limited_proc.communicate = AsyncMock(return_value=(b"", b"Error: 429 Too Many Requests"))
        rate_limited_proc.returncode = 1

        success_proc = AsyncMock()
        success_proc.communicate = AsyncMock(return_value=(b"Hello!", b""))
        success_proc.returncode = 0

        executor = AgentExecutor(adapters={"claude": adapter}, config=fast_retry_config)

        call_count = 0

        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return rate_limited_proc
            return success_proc

        with patch("neurones.core.executor.asyncio.create_subprocess_exec", side_effect=mock_create):
            result = await executor.run_single("claude", "test")

        assert result.success
        assert result.output == "Hello!"
        assert result.retries == 2
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_run_single_rate_limit_exhausted(self, fast_retry_config):
        """Returns rate-limited result when all retries exhausted."""
        adapter = ClaudeAdapter(binary_path="/usr/bin/claude", timeout=30)

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"rate limit exceeded"))
        mock_proc.returncode = 1

        executor = AgentExecutor(adapters={"claude": adapter}, config=fast_retry_config)

        with patch("neurones.core.executor.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.run_single("claude", "test")

        assert not result.success
        assert result.rate_limited
        assert result.retries == 2  # max_retries
        assert result.status_label == "RATE_LIMITED"

    @pytest.mark.asyncio
    async def test_run_single_rate_limit_with_retry_after(self, fast_retry_config):
        """Respects retry-after header from server response."""
        adapter = ClaudeAdapter(binary_path="/usr/bin/claude", timeout=30)

        rate_limited_proc = AsyncMock()
        rate_limited_proc.communicate = AsyncMock(
            return_value=(b"", b"Rate limit exceeded. Retry-After: 0.01")
        )
        rate_limited_proc.returncode = 1

        success_proc = AsyncMock()
        success_proc.communicate = AsyncMock(return_value=(b"OK", b""))
        success_proc.returncode = 0

        executor = AgentExecutor(adapters={"claude": adapter}, config=fast_retry_config)

        call_count = 0

        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return rate_limited_proc if call_count == 1 else success_proc

        with patch("neurones.core.executor.asyncio.create_subprocess_exec", side_effect=mock_create):
            result = await executor.run_single("claude", "test")

        assert result.success
        assert result.retries == 1

    @pytest.mark.asyncio
    async def test_run_single_non_rate_limit_error_no_retry(self):
        """Non-rate-limit errors are NOT retried."""
        adapter = ClaudeAdapter(binary_path="/usr/bin/claude", timeout=30)

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"SyntaxError: invalid"))
        mock_proc.returncode = 1

        executor = AgentExecutor(adapters={"claude": adapter})

        with patch("neurones.core.executor.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.run_single("claude", "test")

        assert not result.success
        assert not result.rate_limited
        assert result.retries == 0

    @pytest.mark.asyncio
    async def test_run_parallel_collects_all_results(self):
        """run_parallel returns results from all agents."""
        adapters = {
            "claude": ClaudeAdapter(binary_path="/usr/bin/claude", timeout=30),
        }

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"Output", b""))
        mock_proc.returncode = 0

        executor = AgentExecutor(adapters=adapters)

        with patch("neurones.core.executor.asyncio.create_subprocess_exec", return_value=mock_proc):
            results = await executor.run_parallel([
                ("claude", "task 1"),
                ("claude", "task 2"),
            ])

        assert len(results) == 2
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_run_parallel_handles_exceptions(self):
        """run_parallel handles exceptions gracefully."""
        adapters = {
            "claude": ClaudeAdapter(binary_path="/usr/bin/claude", timeout=30),
        }

        executor = AgentExecutor(adapters=adapters)

        with patch(
            "neurones.core.executor.asyncio.create_subprocess_exec",
            side_effect=OSError("No such file"),
        ):
            results = await executor.run_parallel([("claude", "test")])

        assert len(results) == 1
        assert not results[0].success


class TestAgentResult:
    """Tests for AgentResult."""

    def test_from_error(self):
        result = AgentResult.from_error("claude", ValueError("test error"))
        assert not result.success
        assert result.returncode == -1
        assert "test error" in result.stderr

    def test_status_label_success(self, success_result):
        assert success_result.status_label == "SUCCESS"

    def test_status_label_success_with_retries(self):
        result = AgentResult(
            agent_name="test", output="ok", success=True, retries=2,
        )
        assert result.status_label == "SUCCESS (retried 2x)"

    def test_status_label_failed(self, failed_result):
        assert failed_result.status_label == "FAILED"

    def test_status_label_timeout(self):
        result = AgentResult(
            agent_name="test",
            output="",
            success=False,
            stderr="Agent timed out after 300s",
        )
        assert result.status_label == "TIMEOUT"

    def test_status_label_rate_limited(self):
        result = AgentResult(
            agent_name="test",
            output="",
            success=False,
            rate_limited=True,
        )
        assert result.status_label == "RATE_LIMITED"

    def test_truncated_output_short(self):
        result = AgentResult(agent_name="test", output="short", success=True)
        assert result.truncated_output == "short"

    def test_truncated_output_long(self):
        result = AgentResult(agent_name="test", output="x" * 600, success=True)
        assert len(result.truncated_output) == 503  # 500 + "..."
        assert result.truncated_output.endswith("...")
