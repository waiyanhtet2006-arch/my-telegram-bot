"""
In-memory conversation history manager per chat.
Keeps last N turns to stay within context limits.
"""
from typing import TypedDict
from collections import defaultdict

MAX_HISTORY_TURNS = 20  # Keep last 20 turns (user+model pairs)


class Message(TypedDict):
    role: str   # "user" or "model"
    text: str


# chat_id -> list of Message dicts
_histories: dict[int, list[Message]] = defaultdict(list)

# chat_id -> personality mode
_personalities: dict[int, str] = defaultdict(lambda: "default")


def add_message(chat_id: int, role: str, text: str) -> None:
    """Append a message to history, trimming if needed."""
    _histories[chat_id].append({"role": role, "text": text})
    # Trim to max turns (each turn = 2 messages)
    max_msgs = MAX_HISTORY_TURNS * 2
    if len(_histories[chat_id]) > max_msgs:
        _histories[chat_id] = _histories[chat_id][-max_msgs:]


def get_history(chat_id: int) -> list[Message]:
    """Return the conversation history for a chat."""
    return list(_histories[chat_id])


def clear_history(chat_id: int) -> None:
    """Clear conversation history for a chat."""
    _histories[chat_id] = []


def set_personality(chat_id: int, mode: str) -> None:
    _personalities[chat_id] = mode
    # Clear history when switching personality so context is fresh
    clear_history(chat_id)


def get_personality(chat_id: int) -> str:
    return _personalities[chat_id]
