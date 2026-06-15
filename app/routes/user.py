"""User and System route for CarbonCompass.

This module provides endpoints for setting user profiles, retrieving global
statistics, and reading application information.
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from app.calculator import estimate_annual_footprint
from app.constants import (
    GLOBAL_AVERAGE_ANNUAL_TONNES,
    INDIA_AVERAGE_ANNUAL_TONNES,
    RATE_LIMIT_WINDOW,
)
from app.models import ProfileRequest, ProfileResponse
from app.security import (
    check_rate_limit,
    get_client_ip,
    sanitize_input,
    validate_session_id,
)
from app.state import get_session_stats, user_profiles

router = APIRouter(prefix="/api/v1", tags=["User"])


@router.post("/profile", response_model=ProfileResponse)
async def set_profile(req: ProfileRequest, request: Request) -> Dict[str, Any]:
    """Set the user's carbon profile and return baseline CO2 calculations.

    Args:
        req (ProfileRequest): Input lifestyle parameters.
        request (Request): FastAPI request context.

    Returns:
        Dict[str, Any]: Profile calculation summary statistics.

    Raises:
        HTTPException: If session validation or rate limits fail.
    """
    request_id = (
        request.state.request_id if hasattr(request.state, "request_id") else "profile"
    )
    ip_address = get_client_ip(request)

    if not check_rate_limit(ip_address, "profile"):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    try:
        validate_session_id(req.session_id)
        sanitize_input(req.country)
        sanitize_input(req.diet)
        sanitize_input(req.transport)
        sanitize_input(req.home_energy)

        user_profiles[req.session_id] = {
            "country": req.country,
            "diet": req.diet,
            "transport": req.transport,
            "home_energy": req.home_energy,
        }

        # Calculate estimated footprint
        base = estimate_annual_footprint(
            req.diet, req.transport, req.home_energy, req.country
        )

        vs_india = (
            "below"
            if base < INDIA_AVERAGE_ANNUAL_TONNES
            else ("above" if base > INDIA_AVERAGE_ANNUAL_TONNES else "at")
        )
        vs_global = "below" if base < GLOBAL_AVERAGE_ANNUAL_TONNES else "above"

        # Determine top opportunity
        opportunities = {
            "heavy_meat": "Switch to a more plant-based diet",
            "meat": "Switch to a more plant-based diet",
            "car": "Switch to public transport or cycling",
            "motorcycle": "Consider public transport for daily commute",
            "heavy_ac": "Optimize AC usage and consider solar",
        }
        top_opp = "Keep up your green habits! 🌱"
        for key, suggestion in opportunities.items():
            lifestyle_string = (
                req.diet.lower() + req.transport.lower() + req.home_energy.lower()
            ).replace(" ", "_")
            if key in lifestyle_string:
                top_opp = suggestion
                break

        return {
            "estimated_annual_co2_tonnes": base,
            "vs_india_average": f"{vs_india} India average (1.9T)",
            "vs_global_average": f"{vs_global} global average (4.8T)",
            "top_reduction_opportunity": top_opp,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        # central endpoint error logger fallback
        import logging

        logger = logging.getLogger("carboncompass")
        logger.error(
            "endpoint_error",
            extra={
                "endpoint": "/api/v1/profile",
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


@router.get("/stats")
async def get_stats(request: Request) -> Dict[str, Any]:
    """Retrieve global usage metrics and server operational statistics.

    Args:
        request (Request): FastAPI request context.

    Returns:
        Dict[str, Any]: Dictionary matching StatsResponse schemas.

    Raises:
        HTTPException: If rate limiting fails.
    """
    request_id = (
        request.state.request_id if hasattr(request.state, "request_id") else "stats"
    )
    ip_address = get_client_ip(request)

    if not check_rate_limit(ip_address, "stats"):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    try:
        return get_session_stats()
    except Exception as e:
        import logging

        logger = logging.getLogger("carboncompass")
        logger.error(
            "endpoint_error",
            extra={
                "endpoint": "/api/v1/stats",
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


@router.get("/about")
async def about(request: Request) -> Dict[str, Any]:
    """Retrieve metadata information and mission statement of CarbonCompass.

    Args:
        request (Request): FastAPI request context.

    Returns:
        Dict[str, Any]: Project information, targets, and Google services utilized.
    """
    # Simply bypass rate limits for metadata as it is very light
    return {
        "app": "CarbonCompass",
        "tagline": "Navigate Towards a Greener Future",
        "version": "1.0.0",
        "live_url": "https://carboncompass-rlzbi2esba-uc.a.run.app/",
        "github": "https://github.com/bikashtiwari603/Carbon-Compass",
        "deployment_region": "us-central1",
        "mission": (
            "Empower every individual to understand measure and reduce "
            "their carbon footprint through AI-powered personalized "
            "insights and gamified eco-actions"
        ),
        "problem_solved": (
            "Most individuals have no idea what their carbon footprint "
            "is or how their daily choices contribute to climate change. "
            "CarbonCompass bridges this awareness gap with simple "
            "tracking personalized AI guidance and actionable "
            "reduction roadmaps"
        ),
        "target_audience": (
            "Climate-conscious individuals students professionals "
            "families anyone wanting to reduce environmental impact"
        ),
        "impact_metrics": {
            "activity_categories": 5,
            "trackable_activities": 20,
            "badges": 9,
            "roadmap_phases": 6,
            "carbon_formulas": 15,
            "languages_supported": ["English"],
        },
        "google_services": [
            "Google Gemini AI",
            "Google Cloud Run",
            "Google Cloud Logging",
            "Google Analytics 4",
            "Google Secret Manager",
            "Google Fonts",
        ],
        "non_commercial": True,
    }
