"""Async parallel subprocess runner for agent execution."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from neurones.adapters.base import AgentAdapter
from neurones.logger import log
from neurones.models.config import AppConfig
from neurones.models.result import AgentResult


class AgentExecutor:
    """Execute agent CLI commands as async subprocesses with rate limit retry."""

    def __init__(self, adapters: dict[str, AgentAdapter], config: AppConfig | None = None):
        self.adapters = adapters
        self._max_retries = config.max_retries if config else 3
        self._retry_base_delay = config.retry_base_delay if config else 5.0
        self._retry_max_delay = config.retry_max_delay if config else 60.0

    async def run_single(self, agent_name: str, prompt: str, **kwargs: Any) -> AgentResult:
        """Run a single agent, retrying on rate limit with exponential backoff."""
        adapter = self.adapters.get(agent_name)
        if adapter is None:
            return AgentResult.from_error(agent_name, ValueError(f"Unknown agent: {agent_name}"))

        cmd = adapter.build_command(prompt, **kwargs)
        log.info("Running %s: %s", agent_name, " ".join(cmd[:5]) + "...")

        total_start = time.monotonic()
        last_result: AgentResult | None = None

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                delay = self._compute_delay(attempt, last_result, adapter)
                log.warning(
                    "%s rate limited (attempt %d/%d), retrying in %.1fs",
                    agent_name, attempt, self._max_retries, delay,
                )
                await asyncio.sleep(delay)

            result = await self._execute_once(agent_name, adapter, cmd)

            if not result.rate_limited:
                result.retries = attempt
                result.duration_seconds = time.monotonic() - total_start
                if attempt > 0:
                    log.info(
                        "%s succeeded after %d retries (%.1fs total)",
                        agent_name, attempt, result.duration_seconds,
                    )
                return result

            last_result = result

        # All retries exhausted — return the last rate-limited result
        assert last_result is not None
        last_result.retries = self._max_retries
        last_result.duration_seconds = time.monotonic() - total_start
        log.error(
            "%s still rate limited after %d retries (%.1fs total)",
            agent_name, self._max_retries, last_result.duration_seconds,
        )
        return last_result

    def _compute_delay(self, attempt: int, last_result: AgentResult | None, adapter: AgentAdapter) -> float:
        """Compute retry delay: use server's retry-after if available, else exponential backoff."""
        if last_result:
            stdout = last_result.output
            stderr = last_result.stderr
            server_delay = adapter.extract_retry_after(stdout, stderr)
            if server_delay is not None:
                return min(server_delay, self._retry_max_delay)

        # Exponential backoff: base * 2^(attempt-1), capped at max
        delay = self._retry_base_delay * (2 ** (attempt - 1))
        return min(delay, self._retry_max_delay)

    async def _execute_once(self, agent_name: str, adapter: AgentAdapter, cmd: list[str]) -> AgentResult:
        """Execute a single subprocess invocation (no retry logic)."""
        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=adapter.timeout
            )
            duration = time.monotonic() - start
            result = adapter.parse_output(stdout, stderr, proc.returncode)
            result.duration_seconds = duration
            log.info(
                "%s completed in %.1fs (exit=%d, output=%d chars, rate_limited=%s)",
                agent_name, duration, proc.returncode, len(result.output), result.rate_limited,
            )
            return result

        except asyncio.TimeoutError:
            duration = time.monotonic() - start
            log.warning("%s timed out after %.1fs", agent_name, duration)
            try:
                proc.kill()  # type: ignore[possibly-undefined]
            except ProcessLookupError:
                pass
            return AgentResult(
                agent_name=agent_name,
                output="",
                success=False,
                returncode=-1,
                stderr=f"Agent timed out after {adapter.timeout}s",
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.monotonic() - start
            log.error("%s failed: %s", agent_name, e)
            result = AgentResult.from_error(agent_name, e)
            result.duration_seconds = duration
            return result

    async def run_parallel(
        self, tasks: list[tuple[str, str]], **kwargs: Any
    ) -> list[AgentResult]:
        """Run multiple agents in parallel and collect results."""
        coros = [self.run_single(agent, prompt, **kwargs) for agent, prompt in tasks]
        results = await asyncio.gather(*coros, return_exceptions=True)

        processed = []
        for i, r in enumerate(results):
            if isinstance(r, AgentResult):
                processed.append(r)
            elif isinstance(r, Exception):
                agent_name = tasks[i][0] if i < len(tasks) else "unknown"
                processed.append(AgentResult.from_error(agent_name, r))
            else:
                processed.append(AgentResult.from_error("unknown", RuntimeError(str(r))))

        return processed
