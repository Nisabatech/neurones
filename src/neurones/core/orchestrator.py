"""The brain — orchestrator that delegates work across agents."""

from __future__ import annotations

import json

from neurones.core.executor import AgentExecutor
from neurones.core.utils import extract_json_block
from neurones.logger import log
from neurones.models.config import AppConfig

ORCHESTRATION_SYSTEM_PROMPT = """\
You are Neurones, an AI orchestrator. You have access to three AI development agents:

AVAILABLE AGENTS:
- claude: Best for reasoning, planning, documentation, debugging, architecture
- gemini: Best for web search, research, quick factual queries, Google ecosystem
- codex: Best for code generation, code review, sandboxed execution, file operations

TASK: Analyze the user's request and create a delegation plan.

RULES:
1. If the task is simple enough for one agent, set "delegate": false and handle it yourself.
2. If the task benefits from multiple agents, create subtasks with specific prompts.
3. Each subtask prompt must be self-contained (the receiving agent has no prior context).
4. You can assign tasks to yourself too.

Respond with ONLY this JSON (no markdown, no explanation):
{
  "delegate": true/false,
  "reasoning": "Brief explanation of your delegation decision",
  "subtasks": [
    {
      "agent": "claude|gemini|codex",
      "prompt": "Specific, self-contained prompt for this agent",
      "priority": "high|medium|low"
    }
  ],
  "self_task": "What you will handle directly (null if delegating everything)"
}
"""

CLAUDE_COORDINATOR_ONLY_POLICY = """\
PRIMARY POLICY:
- The primary agent (claude) is coordinator-only.
- Always set "delegate": true.
- Do not assign any subtask to "claude".
- Always set "self_task": null.
"""


class Orchestrator:
    """Primary agent brain that analyzes tasks and delegates to other agents."""

    def __init__(
        self,
        primary: str,
        adapters: dict,
        executor: AgentExecutor,
        config: AppConfig,
        available_agents: list[str] | None = None,
    ):
        self.primary = primary
        self.adapters = adapters
        self.executor = executor
        self.config = config
        self.available_agents = available_agents or list(adapters.keys())

    async def run(self, prompt: str) -> str:
        """Full orchestration flow: analyze → dispatch → collect → synthesize."""
        log.info("Orchestrating: %s", prompt[:100])

        # Step 1: Ask primary to analyze and create delegation plan
        try:
            plan = await self._analyze(prompt)
        except Exception as e:
            if self._primary_is_coordinator_only():
                log.warning(
                    "Orchestration analysis failed; primary is coordinator-only, "
                    "falling back to worker broadcast: %s",
                    e,
                )
                tasks = self._build_worker_fallback_tasks(prompt)
                if not tasks:
                    raise RuntimeError(
                        "No worker agents available for coordinator-only primary"
                    ) from e
                results = await self.executor.run_parallel(tasks)
                synthesis_prompt = self._build_synthesis_prompt(prompt, results)
                final = await self.executor.run_single(self.primary, synthesis_prompt)
                return final.output

            log.warning("Orchestration analysis failed, falling back to direct: %s", e)
            result = await self.executor.run_single(self.primary, prompt)
            return result.output

        log.info("Delegation plan: delegate=%s, subtasks=%d", plan.get("delegate"), len(plan.get("subtasks", [])))

        if not plan.get("delegate", False):
            if self._primary_is_coordinator_only():
                log.info(
                    "Primary '%s' is coordinator-only; forcing worker delegation",
                    self.primary,
                )
                tasks = self._build_worker_fallback_tasks(prompt)
                if not tasks:
                    raise RuntimeError(
                        "No worker agents available for coordinator-only primary"
                    )
                results = await self.executor.run_parallel(tasks)
                synthesis_prompt = self._build_synthesis_prompt(prompt, results)
                final = await self.executor.run_single(self.primary, synthesis_prompt)
                return final.output

            # Simple task — just run on primary directly
            log.info("No delegation needed, running on primary")
            result = await self.executor.run_single(self.primary, prompt)
            return result.output

        # Step 2: Dispatch subtasks in parallel
        tasks = self._build_dispatch_tasks(plan.get("subtasks", []))

        if not tasks:
            if self._primary_is_coordinator_only():
                log.warning(
                    "No valid subtasks and primary is coordinator-only; "
                    "falling back to worker broadcast",
                )
                tasks = self._build_worker_fallback_tasks(prompt)
                if not tasks:
                    raise RuntimeError(
                        "No worker agents available for coordinator-only primary"
                    )
            else:
                log.warning("No valid subtasks, falling back to direct execution")
                result = await self.executor.run_single(self.primary, prompt)
                return result.output

        log.info("Dispatching %d subtasks in parallel", len(tasks))
        results = await self.executor.run_parallel(tasks)

        # Step 3: Also run primary's self_task if any
        self_task = plan.get("self_task")
        if self_task and not self._primary_is_coordinator_only():
            log.info("Running primary self-task")
            primary_result = await self.executor.run_single(self.primary, self_task)
            results.append(primary_result)
        elif self_task:
            log.info("Ignoring self_task because primary '%s' is coordinator-only", self.primary)

        # Step 4: Synthesize — send all results back to primary
        synthesis_prompt = self._build_synthesis_prompt(prompt, results)
        log.info("Synthesizing %d results", len(results))
        final = await self.executor.run_single(self.primary, synthesis_prompt)
        return final.output

    def _primary_is_coordinator_only(self) -> bool:
        """Whether the primary is restricted to orchestration-only behavior."""
        return self.primary == "claude"

    def _build_worker_fallback_tasks(self, prompt: str) -> list[tuple[str, str]]:
        """Build generic fallback tasks that skip the coordinator-only primary."""
        return [
            (agent_name, prompt)
            for agent_name in self.adapters
            if agent_name != self.primary
        ]

    def _build_dispatch_tasks(self, subtasks: list[dict]) -> list[tuple[str, str]]:
        """Convert plan subtasks into executable tasks, filtering invalid entries."""
        tasks: list[tuple[str, str]] = []
        for subtask in subtasks:
            agent = subtask.get("agent", "")
            task_prompt = subtask.get("prompt")
            if not isinstance(task_prompt, str) or not task_prompt.strip():
                log.warning("Skipping subtask with invalid prompt for agent: %s", agent)
                continue
            if agent not in self.adapters:
                log.warning("Skipping subtask for unavailable agent: %s", agent)
                continue
            if self._primary_is_coordinator_only() and agent == self.primary:
                log.warning(
                    "Skipping subtask for coordinator-only primary agent: %s",
                    agent,
                )
                continue
            tasks.append((agent, task_prompt))
        return tasks

    async def _analyze(self, prompt: str) -> dict:
        """Ask primary agent to create delegation plan."""
        # Build system prompt with only available agents
        available_info = ", ".join(self.available_agents)
        policy_block = (
            f"\n\n{CLAUDE_COORDINATOR_ONLY_POLICY}"
            if self._primary_is_coordinator_only()
            else ""
        )
        analysis_prompt = (
            f"{ORCHESTRATION_SYSTEM_PROMPT}{policy_block}\n\n"
            f"AVAILABLE (installed) AGENTS: {available_info}\n\n"
            f"USER REQUEST:\n{prompt}"
        )

        result = await self.executor.run_single(
            self.primary, analysis_prompt, json_output=True
        )

        if not result.success:
            raise RuntimeError(f"Primary agent failed during analysis: {result.stderr}")

        # Parse JSON from output (handles markdown fences, malformed JSON)
        try:
            cleaned = extract_json_block(result.output)
            plan = json.loads(cleaned)
        except (json.JSONDecodeError, Exception) as e:
            log.warning("Failed to parse delegation JSON: %s", e)
            raise RuntimeError(f"Invalid delegation plan JSON: {e}")

        # Validate the plan is a dict with expected structure
        if not isinstance(plan, dict):
            log.warning("Delegation plan is not a dict: %s", type(plan))
            raise RuntimeError("Delegation plan is not a JSON object")

        if "delegate" not in plan:
            log.warning("Delegation plan missing 'delegate' key")
            raise RuntimeError("Delegation plan missing 'delegate' key")

        return plan

    def _build_synthesis_prompt(self, original_prompt: str, results: list) -> str:
        """Build the prompt that asks primary to merge all results."""
        parts = [f"ORIGINAL TASK: {original_prompt}\n\nRESULTS FROM AGENTS:\n"]
        for r in results:
            status = r.status_label
            parts.append(f"--- {r.agent_name.upper()} [{status}] ---\n{r.output}\n")

        parts.append(
            "\nSynthesize these results into a single, coherent response. "
            "Merge complementary information, resolve conflicts, and present "
            "the best unified answer."
        )
        return "\n".join(parts)
