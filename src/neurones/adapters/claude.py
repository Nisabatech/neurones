"""Claude Code CLI adapter."""

from __future__ import annotations

from neurones.adapters.base import AgentAdapter


class ClaudeAdapter(AgentAdapter):
    """Adapter for Claude Code CLI."""

    name = "claude"
    display_name = "Claude Code"
    provider = "Anthropic"

    def build_command(self, prompt: str, *, json_output: bool = False,
                      model: str | None = None, auto_approve: bool | None = None,
                      system_prompt: str | None = None, max_turns: int | None = None) -> list[str]:
        cmd = [self.binary_path, "-p", prompt]

        if json_output:
            cmd += ["--output-format", "json"]

        effective_model = model or self.default_model
        if effective_model:
            cmd += ["--model", effective_model]

        effective_approve = auto_approve if auto_approve is not None else self.auto_approve
        if effective_approve:
            cmd += ["--permission-mode", "dontAsk"]

        if system_prompt:
            cmd += ["--append-system-prompt", system_prompt]

        effective_max_turns = max_turns
        if effective_max_turns:
            cmd += ["--max-turns", str(effective_max_turns)]

        cmd.extend(self.extra_args)
        return cmd
