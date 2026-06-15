"""Activities route for CarbonCompass.

This module provides endpoints for retrieving trackable activities, logging
carbon footprint data, retrieving the user dashboard, and generating weekly reports.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.cache import get_cached, set_cached
from app.calculator import calculate_co2
from app.constants import (
    ACTIVITIES_DATA,
    GLOBAL_AVERAGE_ANNUAL_TONNES,
    INDIA_AVERAGE_ANNUAL_TONNES,
    RATE_LIMIT_WINDOW,
)
from app.gamification import award_points, check_badges
from app.models import ActivityLogResponse, ActivityRequest
from app.security import (
    check_rate_limit,
    get_client_ip,
    sanitize_input,
    validate_session_id,
)
from app.state import activity_logs, increment_stat, user_points

logger = logging.getLogger("carboncompass")
router = APIRouter(prefix="/api/v1", tags=["Activities"])


@router.get("/activities")
async def get_activities(request: Request) -> Response:
    """Return all trackable activity categories with their carbon emission factors.

    Args:
        request (Request): FastAPI request context.

    Returns:
        Response: JSON response containing categories.
    """
    ip_address = get_client_ip(request)
    if not check_rate_limit(ip_address, "activities"):
        return Response(
            content="Rate limit exceeded. Please try again later.",
            status_code=429,
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    data = get_cached("activities")
    hit = data is not None
    resp = JSONResponse(content=data if hit else ACTIVITIES_DATA)
    resp.headers["X-Cache"] = "HIT" if hit else "MISS"
    if not hit:
        set_cached("activities", ACTIVITIES_DATA, 300)
    return resp


@router.post("/log-activity", response_model=ActivityLogResponse)
async def log_activity(req: ActivityRequest, request: Request) -> Dict[str, Any]:
    """Log a carbon-emitting or green offset activity for a user session.

    Args:
        req (ActivityRequest): Activity registration request data.
        request (Request): FastAPI request context.

    Returns:
        Dict[str, Any]: Details of the logged activity and gamification updates.

    Raises:
        HTTPException: If rate limit exceeded or calculation fails.
    """
    request_id = (
        request.state.request_id
        if hasattr(request.state, "request_id")
        else "log-activity"
    )
    ip_address = get_client_ip(request)

    if not check_rate_limit(ip_address, "log-activity"):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    try:
        validate_session_id(req.session_id)
        sanitize_input(req.activity)
        sanitize_input(req.category)

        co2_kg = calculate_co2(req.activity, req.quantity)

        if req.session_id not in activity_logs:
            activity_logs[req.session_id] = []

        activity_logs[req.session_id].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "category": req.category,
                "activity": req.activity,
                "quantity": req.quantity,
                "unit": req.unit,
                "co2_kg": co2_kg,
            }
        )

        points_earned = award_points(req.session_id, co2_kg)
        increment_stat("total_activities_logged")

        new_badges = check_badges(req.session_id)
        direction = "offset" if co2_kg < 0 else "emitted"

        logger.info(
            "activity_logged",
            extra={
                "endpoint": "/api/v1/log-activity",
                "request_id": request_id,
                "session_id": req.session_id,
                "session": req.session_id,
                "category": req.category,
                "co2_kg": co2_kg,
                "points": points_earned,
            },
        )

        return {
            "co2_kg": co2_kg,
            "points_earned": points_earned,
            "total_points": user_points[req.session_id]["points"],
            "message": (
                f"{'🌱 Great green action!' if co2_kg < 0 else '📝 Activity logged!'} "
                f"{abs(co2_kg):.2f}kg CO2 {direction}"
            ),
            "new_badges": new_badges,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(
            "endpoint_error",
            extra={
                "endpoint": "/api/v1/log-activity",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "request_id": request_id,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Request processing failed. Reference ID: {request_id}",
        ) from e


@router.get("/dashboard/{session_id}")
async def get_dashboard(session_id: str, request: Request) -> Dict[str, Any]:
    """Retrieve the dashboard summary statistics and daily carbon trend for a session.

    Args:
        session_id (str): User session identifier.
        request (Request): FastAPI request context.

    Returns:
        Dict[str, Any]: User stats breakdown, trends, and badge progress.

    Raises:
        HTTPException: If session validation or rate limits fail.
    """
    request_id = (
        request.state.request_id if hasattr(request.state, "request_id") else "dash"
    )
    ip_address = get_client_ip(request)

    if not check_rate_limit(ip_address, "dashboard"):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    try:
        validate_session_id(session_id)
        logs = activity_logs.get(session_id, [])

        total_co2_kg = round(sum(log["co2_kg"] for log in logs if log["co2_kg"] > 0), 2)
        total_offset_kg = round(
            abs(sum(log["co2_kg"] for log in logs if log["co2_kg"] < 0)), 2
        )
        net_co2_kg = round(total_co2_kg - total_offset_kg, 2)

        breakdown: Dict[str, float] = {}
        for log in logs:
            cat = log["category"]
            breakdown[cat] = round(breakdown.get(cat, 0.0) + log["co2_kg"], 2)

        if logs:
            dates = set()
            for log in logs:
                try:
                    dates.add(log["timestamp"][:10])
                except Exception:
                    pass
            days_active = max(len(dates), 1)
        else:
            days_active = 1

        daily_average = round(net_co2_kg / days_active, 2)
        annual_estimate = daily_average * 365 / 1000
        comparison_india = round(annual_estimate - INDIA_AVERAGE_ANNUAL_TONNES, 2)
        comparison_global = round(annual_estimate - GLOBAL_AVERAGE_ANNUAL_TONNES, 2)

        trend = []
        today = datetime.now(timezone.utc).date()
        for i in range(6, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            day_total = round(
                sum(log["co2_kg"] for log in logs if log["timestamp"][:10] == d), 2
            )
            trend.append({"date": d, "co2_kg": day_total})

        positive_breakdown = {k: v for k, v in breakdown.items() if v > 0}
        top_emission_source = (
            max(positive_breakdown, key=lambda k: positive_breakdown[k])
            if positive_breakdown
            else "none"
        )

        up = user_points.get(session_id, {"points": 0, "badges": []})

        return {
            "total_co2_kg": total_co2_kg,
            "total_offset_kg": total_offset_kg,
            "net_co2_kg": net_co2_kg,
            "breakdown": breakdown,
            "daily_average": daily_average,
            "comparison_to_india_average": comparison_india,
            "comparison_to_global_average": comparison_global,
            "trend": trend,
            "top_emission_source": top_emission_source,
            "activities_count": len(logs),
            "points": up["points"],
            "badges": up["badges"],
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(
            "endpoint_error",
            extra={
                "endpoint": f"/api/v1/dashboard/{session_id}",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "request_id": request_id,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Request processing failed. Reference ID: {request_id}",
        ) from e


@router.get("/weekly-report/{session_id}")
async def weekly_report(session_id: str, request: Request) -> Dict[str, Any]:
    """Generate a weekly performance report and carbon summary breakdown.

    Args:
        session_id (str): User session identifier.
        request (Request): FastAPI request context.

    Returns:
        Dict[str, Any]: Weekly footprint metrics and improvement suggestions.

    Raises:
        HTTPException: If validation or rate limits fail.
    """
    request_id = (
        request.state.request_id if hasattr(request.state, "request_id") else "report"
    )
    ip_address = get_client_ip(request)

    if not check_rate_limit(ip_address, "weekly-report"):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    try:
        validate_session_id(session_id)
        logs = activity_logs.get(session_id, [])

        total_co2 = round(sum(log["co2_kg"] for log in logs if log["co2_kg"] > 0), 2)
        total_offset = round(
            abs(sum(log["co2_kg"] for log in logs if log["co2_kg"] < 0)), 2
        )
        net = round(total_co2 - total_offset, 2)

        daily: Dict[str, float] = {}
        for log in logs:
            d = log["timestamp"][:10]
            daily[d] = round(daily.get(d, 0.0) + log["co2_kg"], 2)

        best_day = min(daily, key=lambda k: daily[k]) if daily else "N/A"
        worst_day = max(daily, key=lambda k: daily[k]) if daily else "N/A"

        india_weekly_avg = round(1900.0 / 52.0, 2)
        saved_vs_avg = round(india_weekly_avg - net, 2)

        cat_totals: Dict[str, float] = {}
        for log in logs:
            if log["co2_kg"] > 0:
                cat_totals[log["category"]] = round(
                    cat_totals.get(log["category"], 0.0) + log["co2_kg"], 2
                )

        sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
        improvement_tips = []
        tip_map = {
            "transport": "Try using public transport or cycling for short trips to cut transport emissions.",
            "food": "Consider one more plant-based meal per day to reduce food-related CO2.",
            "home": "Audit your electricity usage — switch to 5-star appliances and LED lighting.",
            "shopping": "Buy fewer new items and consider second-hand or refurbished products.",
        }
        for cat, _ in sorted_cats[:3]:
            improvement_tips.append(
                tip_map.get(cat, "Keep tracking and reducing your footprint! 🌱")
            )

        up = user_points.get(session_id, {"points": 0, "badges": []})

        return {
            "summary": {
                "total_co2_emitted_kg": total_co2,
                "total_co2_offset_kg": total_offset,
                "net_co2_kg": net,
                "activities_count": len(logs),
                "best_day": best_day,
                "worst_day": worst_day,
                "saved_vs_india_avg_kg": saved_vs_avg,
                "points_earned": up["points"],
            },
            "daily_breakdown": daily,
            "category_breakdown": dict(sorted_cats),
            "improvement_tips": (
                improvement_tips
                if improvement_tips
                else ["Start logging activities to get personalised tips! 🌱"]
            ),
            "india_weekly_avg_kg": india_weekly_avg,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(
            "endpoint_error",
            extra={
                "endpoint": f"/api/v1/weekly-report/{session_id}",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "request_id": request_id,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Request processing failed. Reference ID: {request_id}",
        ) from e
