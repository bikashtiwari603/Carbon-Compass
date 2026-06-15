"""Gamification engine for CarbonCompass.

Calculates points earned from carbon reduction/logging activities,
manages user levels, and awards badges based on carbon goals achieved.
"""

import logging
from typing import Any, Dict, List

from app.constants import (
    BADGES_DATA,
    LEVEL_THRESHOLDS,
    MIN_ACTIVITY_POINTS,
    POINTS_PER_CO2_KG,
)
from app.state import activity_logs, user_points

logger = logging.getLogger("carboncompass")

# Expose constants requested at module level
BADGE_DEFINITIONS: List[Dict[str, Any]] = BADGES_DATA
LEVEL_THRESHOLDS_DICT: Dict[str, int] = LEVEL_THRESHOLDS


def get_user_level(points: int) -> str:
    """Determine the user's level name based on accumulated green points.

    Args:
        points (int): Cumulative green points.

    Returns:
        str: The name of the user level.
    """
    current_level = "Seed"
    for level, threshold in LEVEL_THRESHOLDS.items():
        if points >= threshold:
            current_level = level
    return current_level


def get_all_badges() -> List[dict]:
    """Retrieve the complete list of available badges and achievements.

    Returns:
        List[dict]: All badge definition objects.
    """
    return BADGE_DEFINITIONS


def award_points(session_id: str, co2_kg: float) -> int:
    """Calculate and credit green points for a logged carbon activity.

    Points are proportional to the magnitude of emissions/offsets, with a
    guaranteed minimum per activity.

    Args:
        session_id (str): User session ID.
        co2_kg (float): Calculated CO2 impact of the logged activity in kg.

    Returns:
        int: The points earned for this activity.
    """
    if session_id not in user_points:
        user_points[session_id] = {"points": 0, "badges": []}

    old_points = user_points[session_id]["points"]
    # absolute value is used since offsetting green actions have negative CO2
    points = max(
        MIN_ACTIVITY_POINTS,
        int(abs(co2_kg) * POINTS_PER_CO2_KG),
    )
    new_points = old_points + points
    user_points[session_id]["points"] = new_points

    old_level = get_user_level(old_points)
    new_level = get_user_level(new_points)

    if old_level != new_level:
        logger.info(
            "level_up",
            extra={
                "endpoint": "/api/v1/log-activity",
                "request_id": "system",
                "session_id": session_id,
                "session": session_id,
                "new_level": new_level,
                "points": new_points,
            },
        )
    return points


def check_badges(session_id: str) -> List[str]:
    """Evaluate and award any newly unlocked badges based on activity history.

    Args:
        session_id (str): User session ID.

    Returns:
        List[str]: A list of newly awarded badge ID strings.
    """
    if session_id not in user_points:
        user_points[session_id] = {"points": 0, "badges": []}

    up = user_points[session_id]
    logs = activity_logs.get(session_id, [])
    earned = up["badges"]
    new_badges = []

    total_activities = len(logs)
    total_offset = sum(abs(log["co2_kg"]) for log in logs if log["co2_kg"] < 0)
    green_actions = sum(1 for log in logs if log["co2_kg"] < 0)
    public_transport = sum(
        1 for log in logs if log["activity"] in ("metro", "bus", "public_transport")
    )
    trees = sum(1 for log in logs if log["activity"] == "tree_planted")
    recycled_kg = sum(log["quantity"] for log in logs if log["activity"] == "recycled")

    # Assessment conditions
    checks = [
        ("first_log", total_activities >= 1),
        ("eco_warrior", green_actions >= 10 and up["points"] >= 100),
        ("carbon_crusher", total_offset >= 50.0 and up["points"] >= 200),
        ("green_commuter", public_transport >= 5),
        ("tree_hugger", trees >= 3),
        ("recycling_hero", recycled_kg >= 10.0),
        ("solar_champion", up["points"] >= 500),
        ("planet_protector", up["points"] >= 1000),
        (
            "net_zero_hero",
            total_offset >= sum(log["co2_kg"] for log in logs if log["co2_kg"] > 0)
            and total_activities >= 7,
        ),
    ]

    for badge_id, condition in checks:
        if badge_id not in earned and condition:
            earned.append(badge_id)
            new_badges.append(badge_id)
            logger.info(
                "badge_earned",
                extra={
                    "endpoint": "/api/v1/log-activity",
                    "request_id": "system",
                    "session_id": session_id,
                    "session": session_id,
                    "badge_id": badge_id,
                    "total_points": up["points"],
                },
            )

    return new_badges
