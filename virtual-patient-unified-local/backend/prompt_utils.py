"""Reduce LLM input size without changing intent — fewer tokens → lower latency."""

import logging
import re

logger = logging.getLogger(__name__)


def compact_prompt(text: str) -> str:
    """Normalize whitespace: trim lines, collapse long blank runs, single spaces within lines."""
    if not text or not text.strip():
        return ""
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    body = "\n".join(lines)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def truncate_prompt(text: str, max_chars: int) -> str:
    """Hard cap length (e.g. very long admin global prompts). max_chars <= 0 means no limit."""
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    logger.warning("Prompt truncated: %s → %s characters", len(text), max_chars)
    if max_chars <= 3:
        return text[:max_chars]
    return text[: max_chars - 3].rstrip() + "..."
