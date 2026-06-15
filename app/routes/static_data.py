"""Static Data route for CarbonCompass.

This module provides endpoints for retrieving daily tips, gamification badges,
carbon reduction roadmaps, and interesting carbon facts.
"""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.cache import get_cached, set_cached
from app.constants import BADGES_DATA, RATE_LIMIT_WINDOW, ROADMAP_DATA, TIPS_DATA
from app.security import check_rate_limit, get_client_ip

router = APIRouter(prefix="/api/v1", tags=["Static Data"])


@router.get("/tips")
async def get_tips(request: Request) -> Response:
    """Return static daily tips and the current weekly challenges dataset.

    Args:
        request (Request): FastAPI request context.

    Returns:
        Response: The tips dataset JSON response.
    """
    ip_address = get_client_ip(request)
    if not check_rate_limit(ip_address, "tips"):
        return Response(
            content="Rate limit exceeded. Please try again later.",
            status_code=429,
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    data = get_cached("tips")
    hit = data is not None
    resp = JSONResponse(content=data if hit else TIPS_DATA)
    resp.headers["X-Cache"] = "HIT" if hit else "MISS"
    if not hit:
        set_cached("tips", TIPS_DATA, 300)
    return resp


@router.get("/badges")
async def get_badges(request: Request) -> Response:
    """Return all available gamification badges and achievement definitions.

    Args:
        request (Request): FastAPI request context.

    Returns:
        Response: The badges list JSON response.
    """
    ip_address = get_client_ip(request)
    if not check_rate_limit(ip_address, "badges"):
        return Response(
            content="Rate limit exceeded. Please try again later.",
            status_code=429,
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    data = get_cached("badges")
    hit = data is not None
    resp = JSONResponse(content=data if hit else BADGES_DATA)
    resp.headers["X-Cache"] = "HIT" if hit else "MISS"
    if not hit:
        set_cached("badges", BADGES_DATA, 300)
    return resp


@router.get("/roadmap")
async def get_roadmap(request: Request) -> Response:
    """Return the structured 6-phase carbon reduction roadmap.

    Args:
        request (Request): FastAPI request context.

    Returns:
        Response: The roadmap phases JSON response.
    """
    ip_address = get_client_ip(request)
    if not check_rate_limit(ip_address, "roadmap"):
        return Response(
            content="Rate limit exceeded. Please try again later.",
            status_code=429,
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    data = get_cached("roadmap")
    hit = data is not None
    resp = JSONResponse(content=data if hit else ROADMAP_DATA)
    resp.headers["X-Cache"] = "HIT" if hit else "MISS"
    if not hit:
        set_cached("roadmap", ROADMAP_DATA, 300)
    return resp


@router.get("/facts")
async def get_facts(request: Request) -> Response:
    """Return interesting facts about carbon emissions and environmental sustainability.

    Args:
        request (Request): FastAPI request context.

    Returns:
        Response: The carbon facts list JSON response.
    """
    ip_address = get_client_ip(request)
    if not check_rate_limit(ip_address, "facts"):
        return Response(
            content="Rate limit exceeded. Please try again later.",
            status_code=429,
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    facts_payload = {
        "facts": [
            "An average tree absorbs about 21 kg of CO2 per year.",
            "The average carbon footprint of a person in India is 1.9 tonnes per year.",
            "The global average carbon footprint is 4.8 tonnes per year.",
            "Choosing public transport over driving can save up to 2.5 kg of CO2 per trip.",
        ]
    }

    data = get_cached("facts")
    hit = data is not None
    resp = JSONResponse(content=data if hit else facts_payload)
    resp.headers["X-Cache"] = "HIT" if hit else "MISS"
    if not hit:
        set_cached("facts", facts_payload, 300)
    return resp
