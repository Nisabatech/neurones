"""Custom exception hierarchy for Neurones."""


class NeuronError(Exception):
    """Base exception for all Neurones errors."""


class AgentNotFoundError(NeuronError):
    """Raised when a requested agent binary is not found on PATH."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        super().__init__(f"Agent '{agent_name}' not found. Ensure it is installed and on PATH.")


class AgentTimeoutError(NeuronError):
    """Raised when an agent exceeds its configured timeout."""

    def __init__(self, agent_name: str, timeout: int):
        self.agent_name = agent_name
        self.timeout = timeout
        super().__init__(f"Agent '{agent_name}' timed out after {timeout}s.")


class AgentExecutionError(NeuronError):
    """Raised when an agent process exits with a non-zero return code."""

    def __init__(self, agent_name: str, returncode: int, stderr: str = ""):
        self.agent_name = agent_name
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Agent '{agent_name}' failed (exit code {returncode}): {stderr[:200]}")


class OrchestrationError(NeuronError):
    """Raised when the orchestrator fails to parse a delegation plan."""

    def __init__(self, message: str, raw_output: str = ""):
        self.raw_output = raw_output
        super().__init__(message)


class ConfigError(NeuronError):
    """Raised when configuration loading or validation fails."""


class RateLimitError(NeuronError):
    """Raised when an agent hits an API rate limit."""

    def __init__(self, agent_name: str, retry_after: float | None = None):
        self.agent_name = agent_name
        self.retry_after = retry_after
        msg = f"Agent '{agent_name}' hit rate limit"
        if retry_after is not None:
            msg += f" (retry after {retry_after:.0f}s)"
        super().__init__(msg)


class NoAgentsDetectedError(NeuronError):
    """Raised when no AI CLI agents are found on the system."""

    def __init__(self):
        super().__init__(
            "No AI CLI agents detected. Install at least one of:\n"
            "  - Claude Code: https://docs.anthropic.com/en/docs/claude-code\n"
            "  - Gemini CLI:  https://github.com/google-gemini/gemini-cli\n"
            "  - Codex CLI:   https://github.com/openai/codex"
        )
