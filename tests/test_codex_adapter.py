"""Tests for Codex CLI adapter command building."""

from __future__ import annotations

from neurones.adapters.codex import CodexAdapter


class TestCodexAdapter:
    """Tests for CodexAdapter."""

    def test_build_command_uses_single_skip_git_flag(self):
        """--skip-git-repo-check should not be duplicated."""
        adapter = CodexAdapter(
            binary_path="/usr/local/bin/codex",
            extra_args=["--skip-git-repo-check"],
        )

        cmd = adapter.build_command("hello")

        assert cmd.count("--skip-git-repo-check") == 1

    def test_build_command_prompt_is_last(self):
        """Prompt is appended as the final positional argument."""
        adapter = CodexAdapter(binary_path="/usr/local/bin/codex")

        cmd = adapter.build_command("implement feature", json_output=True)

        assert cmd[-1] == "implement feature"
