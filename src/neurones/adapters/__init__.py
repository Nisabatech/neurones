"""Agent adapters for Neurones."""

from neurones.adapters.base import AgentAdapter
from neurones.adapters.claude import ClaudeAdapter
from neurones.adapters.gemini import GeminiAdapter
from neurones.adapters.codex import CodexAdapter
from neurones.adapters.detector import AgentDetector, DetectedAgent

__all__ = [
    "AgentAdapter",
    "ClaudeAdapter",
    "GeminiAdapter",
    "CodexAdapter",
    "AgentDetector",
    "DetectedAgent",
]
