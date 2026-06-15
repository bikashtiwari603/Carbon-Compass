"""AI Chat route for CarbonCompass.

This module provides the chat API endpoint, interfacing with Google Gemini
and managing conversational state and keywords point awarding.
"""

import logging
from typing import Any, Dict, List

import google.generativeai as genai
from fastapi import APIRouter, HTTPException, Request

from app.config import get_settings
from app.constants import ACTION_WORDS, MAX_SESSION_HISTORY, RATE_LIMIT_WINDOW
from app.gamification import get_user_level
from app.models import ChatRequest, ChatResponse
from app.security import (
    check_rate_limit,
    get_client_ip,
    sanitize_input,
    validate_session_id,
)
from app.state import increment_stat, sessions, user_points

logger = logging.getLogger("carboncompass")
router = APIRouter(prefix="/api/v1", tags=["Chat"])

# Retrieve settings and configure the generative model
_SETTINGS = get_settings()
genai.configure(api_key=_SETTINGS.GEMINI_API_KEY)

try:
    _gemini_model = genai.GenerativeModel("gemini-2.0-flash")
except Exception:
    try:
        _gemini_model = genai.GenerativeModel("gemini-1.5-flash-latest")
    except Exception:
        _gemini_model = genai.GenerativeModel("gemini-pro")

GEMINI_SYSTEM_PROMPT = """You are CarbonCompass AI, a friendly expert sustainability assistant with the mission Navigate Towards a Greener Future. You help individuals understand track and reduce their carbon footprint.

You specialize in:
1. Carbon Footprint Calculation
   - Transport: car motorcycle bus train flight
   - Home energy: electricity LPG CNG solar
   - Food: meat dairy vegetarian vegan
   - Shopping: clothing electronics appliances
   - Waste: recycling composting landfill
   - Water usage

2. Personalized Reduction Tips
   - Based on user location diet transport habits
   - Actionable daily weekly monthly goals
   - Cost saving benefits of green actions
   - India-specific tips: public transport BEST DTC Metro, solar subsidies, EV subsidies

3. Carbon Calculations (use these approximate values):
   - Car petrol: 0.21 kg CO2 per km
   - Car diesel: 0.17 kg CO2 per km
   - Motorcycle: 0.11 kg CO2 per km
   - Bus: 0.089 kg CO2 per km
   - Metro/train: 0.041 kg CO2 per km
   - Flight domestic: 0.255 kg CO2 per km per passenger
   - Flight international: 0.195 kg CO2 per km per passenger
   - Electricity India grid: 0.82 kg CO2 per kWh
   - LPG: 2.98 kg CO2 per kg
   - Beef: 27 kg CO2 per kg
   - Chicken: 6.9 kg CO2 per kg
   - Vegetables: 2 kg CO2 per kg average

4. Green Actions and Their Impact
   - Planting trees: 1 tree absorbs 21 kg CO2 per year
   - Solar panel 1kW: saves 1.5 tonnes CO2 per year in India
   - Switching to EV: saves average 1.2 tonnes CO2 per year in India
   - Composting: diverts 50kg food waste per year from landfill

5. Indian Context
   - Average Indian carbon footprint: 1.9 tonnes CO2 per year
   - Global average: 4.8 tonnes CO2 per year
   - Paris Agreement target: under 2 tonnes per person per year
   - India NDC targets and renewable energy goals
   - Government schemes: PM Surya Ghar, EV subsidies, crop residue programs

6. Gamification Guidance
   - Award points for eco-actions
   - Suggest next badges to earn
   - Weekly challenge ideas

Rules:
- Always be encouraging and positive never guilt-tripping
- Give specific numbers and calculations when asked
- Suggest India-relevant alternatives and solutions
- Break down complex topics into simple actionable steps
- Use green leaf and earth emojis naturally
- If mode is quiz ask one carbon literacy question and evaluate answer
- If mode is calculator guide user through calculating their footprint step by step"""


def call_gemini(messages: List[str], session_id: str) -> dict:
    """Call Google Gemini generative AI with system instructions and user history.

    Args:
        messages (List[str]): Compiled prompt sections representing chat context.
        session_id (str): Unique identifier of user session.

    Returns:
        dict: Containing the AI-generated response text under 'response'.
    """
    full_prompt = "\n".join(messages)
    ai_text = None

    try:
        logger.info(
            "gemini_api_called",
            extra={
                "endpoint": "/api/v1/chat",
                "request_id": "chat-generation",
                "session_id": session_id,
                "session": session_id,
            },
        )
        response = _gemini_model.generate_content(full_prompt)
        ai_text = response.text
    except Exception as e:
        logger.error(
            "gemini_api_error",
            extra={
                "endpoint": "/api/v1/chat",
                "request_id": "chat-generation",
                "session_id": session_id,
                "session": session_id,
                "error_type": type(e).__name__,
            },
        )
        # Attempt fallback to other versions
        for fallback_model_name in [
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash",
            "gemini-pro",
        ]:
            try:
                fallback = genai.GenerativeModel(fallback_model_name)
                resp = fallback.generate_content(full_prompt)
                ai_text = resp.text
                break
            except Exception:
                pass

        if not ai_text:
            raise e

    return {"response": ai_text}


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> Dict[str, Any]:
    """Handle chat conversations powered by Google Gemini, tracking session statistics.

    Args:
        req (ChatRequest): The chat request parameters.
        request (Request): FastAPI request context.

    Returns:
        Dict[str, Any]: The ChatResponse payload.
    """
    request_id = (
        request.state.request_id if hasattr(request.state, "request_id") else "chat-req"
    )
    ip_address = get_client_ip(request)

    if not check_rate_limit(ip_address, "chat"):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    validate_session_id(req.session_id)
    message = sanitize_input(req.message)

    if req.session_id not in sessions:
        sessions[req.session_id] = []
        increment_stat("total_sessions")

    history = sessions[req.session_id]

    mode_hint = ""
    if req.mode == "quiz":
        mode_hint = "\n[MODE: QUIZ — Ask the user one carbon literacy question and evaluate their answer.]"
    elif req.mode == "calculator":
        mode_hint = "\n[MODE: CALCULATOR — Guide the user step-by-step through calculating their carbon footprint.]"
    elif req.mode == "tips":
        mode_hint = "\n[MODE: TIPS — Provide actionable personalized eco-tips.]"

    conversation_parts = [GEMINI_SYSTEM_PROMPT + mode_hint]
    # Restrict context window to latest turns
    for h in history[-18:]:
        conversation_parts.append(f"{h['role']}: {h['content']}")
    conversation_parts.append(f"User: {message}")

    try:
        res = call_gemini(conversation_parts, req.session_id)
        ai_text = res["response"]
    except Exception as e:
        logger.error(
            "endpoint_error",
            extra={
                "endpoint": "/api/v1/chat",
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

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ai_text})

    if len(sessions[req.session_id]) > MAX_SESSION_HISTORY:
        sessions[req.session_id] = sessions[req.session_id][-MAX_SESSION_HISTORY:]

    increment_stat("total_messages")

    points_earned = 0
    msg_lower = message.lower()
    if any(w in msg_lower for w in ACTION_WORDS):
        import random

        points_earned = random.randint(5, 15)
        if req.session_id not in user_points:
            user_points[req.session_id] = {"points": 0, "badges": []}
        old_points = user_points[req.session_id]["points"]
        new_points = old_points + points_earned
        user_points[req.session_id]["points"] = new_points

        old_level = get_user_level(old_points)
        new_level = get_user_level(new_points)
        if old_level != new_level:
            logger.info(
                "level_up",
                extra={
                    "endpoint": "/api/v1/chat",
                    "request_id": request_id,
                    "session_id": req.session_id,
                    "session": req.session_id,
                    "new_level": new_level,
                    "points": new_points,
                },
            )

    suggestions = [
        "How can I reduce my transport emissions? 🚇",
        "What's my estimated carbon footprint? 🧮",
        "Give me today's eco-tip 🌱",
    ]

    logger.info(
        "chat_request_processed",
        extra={
            "endpoint": "/api/v1/chat",
            "request_id": request_id,
            "session_id": req.session_id,
            "session": req.session_id,
            "message_length": len(message),
            "points_earned": points_earned,
        },
    )

    return {
        "response": ai_text,
        "suggestions": suggestions,
        "points_earned": points_earned,
        "session_id": req.session_id,
    }
