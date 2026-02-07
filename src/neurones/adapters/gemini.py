"""Gemini CLI adapter."""

from __future__ import annotations

from neurones.adapters.base import AgentAdapter


class GeminiAdapter(AgentAdapter):
    """Adapter for Gemini CLI."""

    name = "gemini"
    display_name = "Gemini CLI"
    provider = "Google"

    def build_command(self, prompt: str, *, json_output: bool = False,
                      model: str | None = None, auto_approve: bool | None = None,
                      system_prompt: str | None = None, max_turns: int | None = None) -> list[str]:
        cmd = [self.binary_path]

        if json_output:
            cmd += ["--output-format", "json"]

        effective_model = model or self.default_model
        if effective_model:
            cmd += ["-m", effective_model]

        effective_approve = auto_approve if auto_approve is not None else self.auto_approve
        if effective_approve:
            cmd.append("-y")

        cmd.extend(self.extra_args)

        # Positional arg must be last
        cmd.append(prompt)
        return cmd

    def _filter_stderr(self, stderr: str) -> str:
        """Filter known Node.js punycode deprecation warning from Gemini CLI."""
        lines = stderr.splitlines()
        filtered = [
            line for line in lines
            if "punycode" not in line.lower()
            and "DeprecationWarning" not in line
        ]
        return "\n".join(filtered).strip()
