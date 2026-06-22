from __future__ import annotations
from typing import List, Tuple

class ChatMemory:
    """Simple in‑process memory for a conversational agent.

    Stores (role, content) tuples where role is either "user" or "assistant".
    """
    def __init__(self) -> None:
        self._history: List[Tuple[str, str]] = []

    def add_message(self, role: str, content: str) -> None:
        """Append a message to the conversation history.
        Args:
            role: "user" or "assistant".
            content: The text of the message.
        """
        self._history.append((role, content))

    def formatted_history(self) -> str:
        """Return the conversation as a plain‑text string for prompts.
        Each line is prefixed with "Human:" or "Assistant:".
        """
        if not self._history:
            return ""
        lines = []
        for role, msg in self._history:
            prefix = "Human:" if role == "user" else "Assistant:"
            lines.append(f"{prefix} {msg}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Reset the stored conversation history."""
        self._history.clear()
