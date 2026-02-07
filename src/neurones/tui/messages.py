"""Textual Message classes for agent events."""

from __future__ import annotations

from textual.message import Message

from neurones.models.result import AgentResult


class AgentOutput(Message):
    """Chunk of output from an agent."""

    def __init__(self, agent_name: str, text: str) -> None:
        super().__init__()
        self.agent_name = agent_name
        self.text = text


class AgentStatusChanged(Message):
    """Agent status changed (idle, running, success, failed, timeout)."""

    def __init__(self, agent_name: str, status: str) -> None:
        super().__init__()
        self.agent_name = agent_name
        self.status = status


class AgentCompleted(Message):
    """Agent finished execution."""

    def __init__(self, result: AgentResult) -> None:
        super().__init__()
        self.result = result


class OrchestrationStarted(Message):
    """Orchestration flow started."""

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self.prompt = prompt


class OrchestrationCompleted(Message):
    """Orchestration flow completed."""

    def __init__(self, output: str) -> None:
        super().__init__()
        self.output = output


class PromptSubmitted(Message):
    """User submitted a prompt from the input bar."""

    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value


class ModeChanged(Message):
    """User changed the execution mode."""

    def __init__(self, mode: str) -> None:
        super().__init__()
        self.mode = mode
