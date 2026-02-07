"""Codex CLI adapter."""

from __future__ import annotations

from neurones.adapters.base import AgentAdapter


class CodexAdapter(AgentAdapter):
    """Adapter for Codex CLI."""

    name = "codex"
    display_name = "Codex CLI"
    provider = "OpenAI"

    def build_command(self, prompt: str, *, json_output: bool = False,
                      model: str | None = None, auto_approve: bool | None = None,
                      system_prompt: str | None = None, max_turns: int | None = None) -> list[str]:
        cmd = [self.binary_path, "exec"]

        effective_model = model or self.default_model
        if effective_model:
            cmd += ["-m", effective_model]

        effective_approve = auto_approve if auto_approve is not None else self.auto_approve
        if effective_approve:
            cmd.append("--full-auto")

        if json_output:
            cmd.append("--json")

        cmd.extend(self.extra_args)

        # Prompt must be last
        cmd.append(prompt)
        return cmd
