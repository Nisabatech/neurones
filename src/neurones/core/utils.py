"""Utility functions for Neurones core."""

from __future__ import annotations

import re

from json_repair import repair_json


def clean_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\x1b\[.*?[@-~]")
    return ansi_pattern.sub("", text)


def extract_json_block(text: str) -> str:
    """Extract and repair a JSON block from text that may contain markdown fences or extra text.

    Uses json-repair to handle malformed JSON from LLM outputs.
    """
    # Try to find JSON in markdown code fences first
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try to find raw JSON object
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        text = text[brace_start:brace_end + 1]

    # Use json-repair to fix common LLM JSON issues
    return repair_json(text, return_objects=False)
