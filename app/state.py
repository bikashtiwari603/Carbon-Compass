"""State management module for CarbonCompass.

This module houses all in-memory dictionaries representing session history,
user profiles, gamification points, activity logs, statistics, and rate limiting data,
exposing thread-safe functions to manipulate them.
"""

import threading
import time
from typing import Any, Dict, List

# Reentrant lock to ensure thread-safety for multi-threaded uvicorn deployments
_STATE_LOCK = threading.RLock()

# Time when application started
app_start_time: float = time.time()

# In-memory dictionaries
rate_limit_store: Dict[str, List[float]] = {}
sessions: Dict[str, List[Dict[str, str]]] = {}
user_profiles: Dict[str, Dict[str, str]] = {}
user_points: Dict[str, Dict[str, Any]] = {}
activity_logs: Dict[str, List[Dict[str, Any]]] = {}

stats: Dict[str, int] = {
    "total_sessions": 0,
    "total_messages": 0,
    "total_activities_logged": 0,
    "cache_hits": 0,
}


def reset_session(session_id: str) -> None:
    """Clear all stored state associated with a given session identifier.

    Args:
        session_id (str): The session ID to wipe clean.
    """
    with _STATE_LOCK:
        if session_id in sessions:
            sessions[session_id].clear()
        if session_id in user_profiles:
            del user_profiles[session_id]
        if session_id in user_points:
            del user_points[session_id]
        if session_id in activity_logs:
            del activity_logs[session_id]


def get_session_stats() -> dict:
    """Return a dictionary containing the copy of global application statistics.

    Returns:
        dict: The state of stats including calculating current uptime.
    """
    with _STATE_LOCK:
        current_stats: Dict[str, Any] = stats.copy()
    current_stats["uptime_seconds"] = round(time.time() - app_start_time, 2)
    return current_stats



def increment_stat(stat_name: str, amount: int = 1) -> None:
    """Increment a specific application statistic counter.

    Args:
        stat_name (str): The key in the stats dictionary.
        amount (int): The increment value. Defaults to 1.
    """
    with _STATE_LOCK:
        if stat_name in stats:
            stats[stat_name] += amount


def add_message(session_id: str, role: str, content: str) -> None:
    """Append a message turn to the session chat history.

    Args:
        session_id (str): Unique session identifier.
        role (str): The role (e.g. user, assistant).
        content (str): Text message content.
    """
    with _STATE_LOCK:
        if session_id not in sessions:
            sessions[session_id] = []
            increment_stat("total_sessions")
        sessions[session_id].append({"role": role, "content": content})
