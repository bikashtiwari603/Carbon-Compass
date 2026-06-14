"""
CarbonCompass API — Navigate Towards a Greener Future

A production-ready FastAPI backend for the CarbonCompass 
carbon footprint tracking and reduction platform.
Built for PromptWars Challenge 3 by Hack2skill x GDG.

This module provides:
    - AI-powered chat via Google Gemini (gemini-1.5-flash)
    - Carbon footprint calculation for 20+ activity types
    - Gamification engine with points, badges, and levels
    - 6-phase personalized carbon reduction roadmap
    - 30-question carbon literacy quiz engine
    - Weekly AI-generated personal carbon reports
    - Google Cloud Logging structured observability
    - Comprehensive security middleware stack
    - In-memory caching with TTL support
    - Rate limiting per endpoint per IP address

Google Services Integrated:
    - Google Gemini API: Conversational AI engine
    - Google Cloud Run: Serverless deployment
    - Google Cloud Logging: Structured request logging
    - Google Analytics 4: User behavior tracking
    - Google Secret Manager: Secure key management

Architecture:
    - Stateless request handling
    - In-memory session management (resets on redeploy)
    - Cache-aside pattern for static data endpoints
    - Middleware-first security (headers, rate limit, sanitization)

Author: Bikash Tiwari
Repository: https://github.com/bikashtiwari603/Carbon-Compass
Version: 1.0.0
Competition: PromptWars Challenge 3 — Carbon Footprint Tracker
"""

# =============================================================================
# STANDARD LIBRARY IMPORTS
# =============================================================================
import os
import re
import time
import uuid
import random
import unicodedata
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from functools import lru_cache

# =============================================================================
# THIRD-PARTY IMPORTS  
# =============================================================================
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

# =============================================================================
# GOOGLE CLOUD IMPORTS
# =============================================================================
try:
    import google.cloud.logging
    from google.cloud.logging.handlers import CloudLoggingHandler
    CLOUD_LOGGING_AVAILABLE: bool = True
except ImportError:
    CLOUD_LOGGING_AVAILABLE: bool = False

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

# Application metadata
APP_NAME: str = "CarbonCompass"
APP_VERSION: str = "1.0.0"
APP_TAGLINE: str = "Navigate Towards a Greener Future"
APP_DESCRIPTION: str = (
    "AI-powered carbon footprint tracking and reduction platform"
)

# Carbon emission factors (kg CO2 per unit)
# Source: IPCC AR6, India CEF 2023, Our World in Data
EMISSION_FACTORS: Dict[str, float] = {
    "car_petrol": 0.21,        # kg CO2 per km
    "car_diesel": 0.17,        # kg CO2 per km
    "motorcycle": 0.11,        # kg CO2 per km
    "bus": 0.089,              # kg CO2 per km
    "metro": 0.041,            # kg CO2 per km
    "flight_domestic": 0.255,  # kg CO2 per km per passenger
    "flight_international": 0.195,  # kg CO2 per km per passenger
    "electricity": 0.82,       # kg CO2 per kWh (India grid CEF)
    "lpg": 2.98,               # kg CO2 per kg
    "cng": 2.79,               # kg CO2 per kg
    "beef": 27.0,              # kg CO2 per kg food
    "chicken": 6.9,            # kg CO2 per kg food
    "fish": 5.4,               # kg CO2 per kg food
    "vegetables": 2.0,         # kg CO2 per kg food
    "dairy": 3.2,              # kg CO2 per kg food
    "clothing": 10.0,          # kg CO2 per item
    "electronics": 70.0,       # kg CO2 per item
    "appliances": 200.0,       # kg CO2 per item
    "tree_planted": -21.0,     # kg CO2 absorbed per year
    "recycled": -0.5,          # kg CO2 saved per kg recycled
    "composted": -0.5,         # kg CO2 saved per kg composted
    "public_transport": -2.5,  # kg CO2 saved per trip vs car
}

# India carbon benchmarks (tonnes CO2 per year)
INDIA_AVERAGE_ANNUAL_TONNES: float = 1.9
GLOBAL_AVERAGE_ANNUAL_TONNES: float = 4.8
PARIS_TARGET_ANNUAL_TONNES: float = 2.0

# Rate limiting configuration
CHAT_RATE_LIMIT: int = 10        # requests per minute for /chat
DEFAULT_RATE_LIMIT: int = 60     # requests per minute for other endpoints
RATE_LIMIT_WINDOW: int = 60      # window size in seconds

# Session and input limits
MAX_SESSION_HISTORY: int = 20    # maximum messages stored per session
MAX_MESSAGE_LENGTH: int = 2000   # maximum user message character length
MIN_MESSAGE_LENGTH: int = 1      # minimum user message character length
MAX_SESSION_ID_LENGTH: int = 100 # maximum session ID character length
MAX_REPEAT_CHARS: int = 100      # max consecutive repeated characters allowed

# Cache configuration
CACHE_TTL_SECONDS: int = 300     # 5 minutes cache TTL for static endpoints

# Gamification thresholds
POINTS_PER_CO2_KG: int = 10     # green points awarded per kg CO2 unit
MIN_ACTIVITY_POINTS: int = 5     # minimum points per logged activity
TIP_COMPLETION_POINTS: int = 25  # points for completing a daily tip
QUIZ_CORRECT_POINTS: int = 10    # points per correct quiz answer

# Level point thresholds
LEVEL_THRESHOLDS: Dict[str, int] = {
    "Seed": 0,
    "Sapling": 100,
    "Tree": 300,
    "Forest": 600,
    "Planet Protector": 1000,
}

# Request size limit
MAX_REQUEST_SIZE_BYTES: int = 1_000_000  # 1 MB maximum request size

# Security: allowed characters in session ID
SESSION_ID_PATTERN: re.Pattern = re.compile(r'^[a-zA-Z0-9_-]+$')

# Gemini API setup
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# Why: Fail fast at startup rather than on first request
# so Cloud Run health checks catch misconfiguration immediately
if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
    raise RuntimeError("GEMINI_API_KEY environment variable not set")

genai.configure(api_key=GEMINI_API_KEY)

# Try models in order of preference — newest first
try:
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")
    _selected_model = "gemini-2.0-flash"
except Exception:
    try:
        gemini_model = genai.GenerativeModel("gemini-1.5-flash-latest")
        _selected_model = "gemini-1.5-flash-latest"
    except Exception:
        gemini_model = genai.GenerativeModel("gemini-pro")
        _selected_model = "gemini-pro"

# Static Datasets
ACTIVITIES_DATA: Dict[str, Any] = {
    "categories": [
        {
            "id": "transport",
            "name": "Transport 🚗",
            "color": "#FF6B6B",
            "icon": "🚗",
            "activities": [
                {"id": "car_petrol", "name": "Car (Petrol)", "unit": "km", "co2_per_unit": 0.21, "icon": "🚗"},
                {"id": "car_diesel", "name": "Car (Diesel)", "unit": "km", "co2_per_unit": 0.17, "icon": "🚙"},
                {"id": "motorcycle", "name": "Motorcycle", "unit": "km", "co2_per_unit": 0.11, "icon": "🏍️"},
                {"id": "bus", "name": "Bus", "unit": "km", "co2_per_unit": 0.089, "icon": "🚌"},
                {"id": "metro", "name": "Metro/Train", "unit": "km", "co2_per_unit": 0.041, "icon": "🚇"},
                {"id": "flight_domestic", "name": "Domestic Flight", "unit": "km", "co2_per_unit": 0.255, "icon": "✈️"},
                {"id": "flight_international", "name": "International Flight", "unit": "km", "co2_per_unit": 0.195, "icon": "🌍"},
            ],
        },
        {
            "id": "home",
            "name": "Home Energy 🏠",
            "color": "#4ECDC4",
            "icon": "🏠",
            "activities": [
                {"id": "electricity", "name": "Electricity", "unit": "kWh", "co2_per_unit": 0.82, "icon": "⚡"},
                {"id": "lpg", "name": "LPG Cooking Gas", "unit": "kg", "co2_per_unit": 2.98, "icon": "🔥"},
                {"id": "cng", "name": "CNG", "unit": "kg", "co2_per_unit": 2.79, "icon": "⛽"},
            ],
        },
        {
            "id": "food",
            "name": "Food 🍽️",
            "color": "#45B7D1",
            "icon": "🍽️",
            "activities": [
                {"id": "beef", "name": "Beef", "unit": "kg", "co2_per_unit": 27.0, "icon": "🥩"},
                {"id": "chicken", "name": "Chicken", "unit": "kg", "co2_per_unit": 6.9, "icon": "🍗"},
                {"id": "fish", "name": "Fish", "unit": "kg", "co2_per_unit": 5.4, "icon": "🐟"},
                {"id": "vegetables", "name": "Vegetables", "unit": "kg", "co2_per_unit": 2.0, "icon": "🥦"},
                {"id": "dairy", "name": "Dairy Products", "unit": "kg", "co2_per_unit": 3.2, "icon": "🥛"},
            ],
        },
        {
            "id": "shopping",
            "name": "Shopping 🛍️",
            "color": "#96CEB4",
            "icon": "🛍️",
            "activities": [
                {"id": "clothing", "name": "Clothing", "unit": "item", "co2_per_unit": 10.0, "icon": "👕"},
                {"id": "electronics", "name": "Electronics", "unit": "item", "co2_per_unit": 70.0, "icon": "📱"},
                {"id": "appliances", "name": "Appliances", "unit": "item", "co2_per_unit": 200.0, "icon": "🏠"},
            ],
        },
        {
            "id": "green_actions",
            "name": "Green Actions 🌱",
            "color": "var(--accent-green)",
            "icon": "🌱",
            "activities": [
                {"id": "tree_planted", "name": "Tree Planted", "unit": "tree", "co2_per_unit": -21.0, "icon": "🌳"},
                {"id": "recycled", "name": "Recycling", "unit": "kg", "co2_per_unit": -0.5, "icon": "♻️"},
                {"id": "composted", "name": "Composting", "unit": "kg", "co2_per_unit": -0.5, "icon": "🌿"},
                {"id": "public_transport", "name": "Chose Public Transport instead of Car", "unit": "trip", "co2_per_unit": -2.5, "icon": "🚌"},
            ],
        },
    ]
}

BADGES_DATA: List[Dict[str, Any]] = [
    {"id": "first_log", "name": "First Step 🌱", "description": "Log your first activity", "points_required": 0, "activities_required": 1, "icon": "🌱", "color": "var(--accent-green)"},
    {"id": "eco_warrior", "name": "Eco Warrior ⚔️", "description": "Log 10 green actions", "points_required": 100, "activities_required": 10, "icon": "⚔️", "color": "#4ECDC4"},
    {"id": "carbon_crusher", "name": "Carbon Crusher 💪", "description": "Offset 50kg of CO2", "points_required": 200, "activities_required": 0, "icon": "💪", "color": "#45B7D1"},
    {"id": "green_commuter", "name": "Green Commuter 🚇", "description": "Log 5 public transport trips", "points_required": 0, "activities_required": 5, "icon": "🚇", "color": "#96CEB4"},
    {"id": "tree_hugger", "name": "Tree Hugger 🌳", "description": "Plant 3 trees", "points_required": 0, "activities_required": 3, "icon": "🌳", "color": "var(--accent-green)"},
    {"id": "recycling_hero", "name": "Recycling Hero ♻️", "description": "Recycle 10kg of waste", "points_required": 0, "activities_required": 0, "icon": "♻️", "color": "#FF6B6B"},
    {"id": "solar_champion", "name": "Solar Champion ☀️", "description": "Earn 500 green points", "points_required": 500, "activities_required": 0, "icon": "☀️", "color": "#FFD700"},
    {"id": "planet_protector", "name": "Planet Protector 🌍", "description": "Earn 1000 green points", "points_required": 1000, "activities_required": 0, "icon": "🌍", "color": "#FF6B00"},
    {"id": "net_zero_hero", "name": "Net Zero Hero 🏆", "description": "Achieve net zero for a week", "points_required": 0, "activities_required": 0, "icon": "🏆", "color": "#f4d03f"},
]

TIPS_DATA: Dict[str, Any] = {
    "daily_tips": [
        {"id": 1, "category": "transport", "tip": "Take the metro instead of driving today — saves 0.8kg CO2 for a 5km trip", "impact": "Low", "savings_co2_kg": 0.8, "icon": "🚇"},
        {"id": 2, "category": "food", "tip": "Try one plant-based meal today — even one meatless meal saves 1.5kg CO2", "impact": "Medium", "savings_co2_kg": 1.5, "icon": "🥗"},
        {"id": 3, "category": "home", "tip": "Switch off lights and fans when leaving a room — saves up to 0.5kWh daily", "impact": "Low", "savings_co2_kg": 0.4, "icon": "💡"},
        {"id": 4, "category": "shopping", "tip": "Carry a reusable bag today — plastic bags take 500 years to decompose", "impact": "Low", "savings_co2_kg": 0.1, "icon": "🛍️"},
        {"id": 5, "category": "green", "tip": "Start a small compost bin — diverts food waste from landfill producing methane", "impact": "Medium", "savings_co2_kg": 0.5, "icon": "🌿"},
    ],
    "weekly_challenge": {
        "title": "Car-Free Week Challenge 🚗❌",
        "description": "Avoid driving for 7 days. Use metro bus cycle or walk instead.",
        "reward_points": 200,
        "estimated_co2_saved_kg": 14.7,
        "icon": "🏆",
    },
}

ROADMAP_DATA: Dict[str, Any] = {
    "phases": [
        {
            "phase": 1,
            "title": "Awareness 🌱",
            "duration": "Week 1",
            "description": "Understand your current carbon footprint baseline",
            "color": "#FF6B6B",
            "actions": ["Log all daily activities for 7 days", "Complete carbon footprint quiz", "Identify your top 3 emission sources", "Set your reduction goal"],
            "milestone": "Know your baseline CO2 number",
        },
        {
            "phase": 2,
            "title": "Quick Wins 🎯",
            "duration": "Week 2-3",
            "description": "Make easy low-effort changes with immediate impact",
            "color": "#FF8E53",
            "actions": ["Switch to LED bulbs", "Carry reusable bags and bottles", "Reduce one meat meal per week", "Unplug devices not in use"],
            "milestone": "Reduce footprint by 10%",
        },
        {
            "phase": 3,
            "title": "Transport Shift 🚇",
            "duration": "Month 2",
            "description": "Transform how you move — biggest impact category",
            "color": "#4ECDC4",
            "actions": ["Use public transport for work commute", "Walk or cycle for trips under 2km", "Combine errands into single trips", "Consider carpooling"],
            "milestone": "Reduce transport emissions by 30%",
        },
        {
            "phase": 4,
            "title": "Home Green 🏠",
            "duration": "Month 3",
            "description": "Make your home more energy efficient",
            "color": "#45B7D1",
            "actions": ["Audit home electricity consumption", "Install energy efficient appliances", "Optimize AC usage to 24 degrees", "Explore rooftop solar under PM Surya Ghar scheme"],
            "milestone": "Reduce home energy emissions by 25%",
        },
        {
            "phase": 5,
            "title": "Food and Lifestyle 🥗",
            "duration": "Month 4",
            "description": "Transform diet and consumption habits",
            "color": "#96CEB4",
            "actions": ["Adopt flexitarian diet reducing meat by 50%", "Buy local and seasonal produce", "Start home composting", "Reduce food waste with meal planning"],
            "milestone": "Reduce food footprint by 40%",
        },
        {
            "phase": 6,
            "title": "Carbon Champion 🏆",
            "duration": "Month 5-6",
            "description": "Offset remaining emissions and inspire others",
            "color": "var(--accent-green)",
            "actions": ["Plant trees through verified programs", "Calculate and offset remaining footprint", "Share your journey on social media", "Join local environmental groups"],
            "milestone": "Achieve net zero lifestyle",
        },
    ]
}

SYSTEM_PROMPT: str = """You are CarbonCompass AI, a friendly expert sustainability assistant with the mission Navigate Towards a Greener Future. You help individuals understand track and reduce their carbon footprint.

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

ACTION_WORDS: set = {"planted", "switched", "reduced", "recycled", "composted", "walked", "cycled", "saved"}

_CO2_LOOKUP: Dict[str, float] = {}
for cat in ACTIVITIES_DATA["categories"]:
    for act in cat["activities"]:
        _CO2_LOOKUP[act["id"]] = act["co2_per_unit"]

# =============================================================================
# LOGGING SETUP
# =============================================================================

logger = logging.getLogger("carboncompass")
logger.setLevel(logging.INFO)

if CLOUD_LOGGING_AVAILABLE:
    try:
        # Why: Set up structured logging for Google Cloud Run
        cloud_client = google.cloud.logging.Client()
        cloud_client.setup_logging()
        logger.info("Google Cloud Logging initialised.")
    except Exception:
        logging.basicConfig(level=logging.INFO)
        logger.info("Falling back to standard logging due to initialization error.")
else:
    logging.basicConfig(level=logging.INFO)
    logger.info("Falling back to standard logging.")

# =============================================================================
# PYDANTIC REQUEST MODELS
# =============================================================================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=100)
    mode: str = Field(default="general")


class ActivityRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    category: str
    activity: str
    quantity: float
    unit: str


class ProfileRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    country: str = Field(default="India")
    diet: str = ""
    transport: str = ""
    home_energy: str = ""

# =============================================================================
# PYDANTIC RESPONSE MODELS
# =============================================================================

class ChatResponse(BaseModel):
    """Response model for the AI chat endpoint.
    
    Contains the AI-generated response, suggested follow-up
    questions, points earned for the interaction, and the
    session identifier for continuity.
    """
    response: str = Field(
        ..., 
        description="AI-generated response text from Google Gemini"
    )
    suggestions: List[str] = Field(
        ..., 
        description="Three suggested follow-up questions",
        min_length=3,
        max_length=3
    )
    points_earned: int = Field(
        ..., 
        ge=0, 
        description="Green points earned for this interaction"
    )
    session_id: str = Field(
        ..., 
        description="Session identifier for conversation continuity"
    )

class ActivityLogResponse(BaseModel):
    """Response model for the activity logging endpoint.
    
    Returns the calculated CO2 impact, points awarded,
    cumulative session totals, and any newly earned badges.
    """
    co2_kg: float = Field(
        ..., 
        description="CO2 equivalent in kilograms (negative for green actions)"
    )
    points_earned: int = Field(
        ..., 
        ge=0, 
        description="Green points earned for this activity"
    )
    total_points: int = Field(
        ..., 
        ge=0, 
        description="Cumulative green points for this session"
    )
    message: str = Field(
        ..., 
        description="Human-readable confirmation message"
    )
    new_badges: List[str] = Field(
        default_factory=list, 
        description="List of newly earned badge IDs"
    )

class HealthResponse(BaseModel):
    """Response model for the health check endpoint."""
    status: str = Field(..., description="Service status: ok or degraded")
    app: str = Field(..., description="Application name")
    tagline: str = Field(..., description="Application tagline")
    version: str = Field(..., description="Semantic version string")

class StatsResponse(BaseModel):
    """Response model for application statistics endpoint."""
    total_sessions: int = Field(..., ge=0, description="Total unique sessions")
    total_messages: int = Field(..., ge=0, description="Total chat messages processed")
    total_activities_logged: int = Field(..., ge=0, description="Total activities logged")
    uptime_seconds: float = Field(..., ge=0, description="Seconds since app startup")
    cache_hits: int = Field(..., ge=0, description="Total cache hits across all endpoints")

class ProfileResponse(BaseModel):
    """Response model for user carbon profile endpoint."""
    estimated_annual_co2_tonnes: float = Field(
        ..., 
        description="Estimated annual CO2 in tonnes based on lifestyle"
    )
    vs_india_average: str = Field(
        ..., 
        description="Comparison to India average (1.9T/year)"
    )
    vs_global_average: str = Field(
        ..., 
        description="Comparison to global average (4.8T/year)"
    )
    top_reduction_opportunity: str = Field(
        ..., 
        description="Single highest-impact action recommended"
    )

# =============================================================================
# FASTAPI APPLICATION INITIALIZATION
# =============================================================================

app_start_time: float = time.time()

app = FastAPI(
    title=APP_NAME,
    description=f"""
## {APP_NAME} — {APP_TAGLINE}

{APP_DESCRIPTION}

Built for **PromptWars Challenge 3** by Hack2skill x GDG.

### Core Features
* **AI Chat** — Google Gemini powered personalized carbon advice
* **Activity Tracker** — 20+ activities with validated CO2 factors
* **Gamification** — Points, 9 badges, and 5 progression levels  
* **Reduction Roadmap** — 6 structured phases to net zero
* **Carbon Quiz** — 30 questions across 5 topic categories
* **Weekly Reports** — AI-generated trend analysis and tips

### Google Services
| Service | Purpose |
|---------|---------|
| Google Gemini API | Conversational AI engine |
| Google Cloud Run | Serverless deployment |
| Google Cloud Logging | Structured observability |
| Google Analytics 4 | User behavior tracking |
| Google Secret Manager | Secure key management |

### India Context
Average Indian footprint: **1.9T CO2/year** 
(vs global average 4.8T — already under Paris target of 2T)

### Rate Limits
* `/api/v1/chat`: 10 requests/minute per IP
* All other endpoints: 60 requests/minute per IP
    """,
    version=APP_VERSION,
    contact={
        "name": "Bikash Tiwari",
        "url": "https://github.com/bikashtiwari603/Carbon-Compass",
    },
    license_info={
        "name": "Non-Commercial Educational Use",
    },
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

startup_ms: float = round((time.time() - app_start_time) * 1000, 2)
logger.info(
    "app_startup",
    extra={
        "endpoint": "startup",
        "request_id": "startup",
        "version": APP_VERSION,
        "env": os.getenv("ENV", "production"),
        "startup_ms": startup_ms,
    }
)

# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to reject oversized requests before processing.
    
    Prevents denial-of-service attacks via large request bodies.
    Checks Content-Length header and rejects anything over
    MAX_REQUEST_SIZE_BYTES without reading the full body.
    
    Attributes:
        max_size: Maximum allowed request size in bytes.
    """
    
    def __init__(self, app: Any, max_size: int = MAX_REQUEST_SIZE_BYTES) -> None:
        """Initialize middleware with configurable size limit.
        
        Args:
            app: The ASGI application instance.
            max_size: Maximum request size in bytes.
        """
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Check request size and reject if over limit.
        
        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or endpoint handler.
            
        Returns:
            Response from next handler, or 413 if too large.
        """
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            logger.warning(
                "request_too_large",
                extra={
                    "content_length": content_length,
                    "max_size": self.max_size,
                    "client_ip": request.client.host if request.client else "unknown",
                }
            )
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body too large. Maximum size: {self.max_size} bytes."}
            )
        return await call_next(request)

app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next: Any) -> Response:
    """Middleware to inject standard security response headers.
    
    Args:
        request: Incoming HTTP request.
        call_next: Next handler in the ASGI stack.
        
    Returns:
        HTTP Response with security headers attached.
    """
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(self), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://www.googletagmanager.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com; "
        "font-src https://fonts.gstatic.com; "
        "connect-src 'self'; "
        "img-src 'self' data:;"
    )
    return response

@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Any) -> Response:
    """Middleware to generate and inject unique request correlation ID.
    
    Args:
        request: Incoming HTTP request.
        call_next: Next handler in the ASGI stack.
        
    Returns:
        HTTP Response with X-Request-ID header attached.
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    ip = get_client_ip(request)
    logger.info(
        "request_received",
        extra={
            "endpoint": request.url.path,
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "ip": ip,
        }
    )
    
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# =============================================================================
# IN-MEMORY STATE MANAGEMENT
# =============================================================================

rate_limit_store: Dict[str, List[float]] = {}
_cache: Dict[str, Dict[str, Any]] = {}
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

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def sanitize_input(text: str) -> str:
    """Remove dangerous content from user-provided input.
    
    Strips HTML tags, script content, null bytes, and 
    normalizes unicode to prevent injection attacks and
    ensure consistent text processing.
    
    Args:
        text: Raw user input string to sanitize.
        
    Returns:
        Sanitized string safe for processing.
        
    Raises:
        HTTPException: 400 if input contains null bytes or
            excessive repeated characters indicating abuse.
    """
    # Remove script tags and content
    text = re.sub(r"<script[\s\S]*?>[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    # Strip all HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove null bytes
    if "\x00" in text:
        raise HTTPException(status_code=400, detail="Invalid characters in input.")
    # Check for excessively repeated characters
    if re.search(r"(.)\1{99,}", text):
        raise HTTPException(status_code=400, detail="Input contains excessively repeated characters.")
    # Why: KFKC normalization handles visually identical unicode 
    # characters that are technically different code points
    normalized_text = unicodedata.normalize("NFKC", text)
    return normalized_text.strip()

def validate_session_id(session_id: str) -> bool:
    """Validate session ID format against allowed character pattern.
    
    Args:
        session_id: Session identifier string.
        
    Returns:
        True if valid.
        
    Raises:
        HTTPException: 400 if session ID format is invalid.
    """
    if not SESSION_ID_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID format.")
    return True

def get_client_ip(request: Request) -> str:
    """Extract client IP address from request.
    
    Args:
        request: The incoming HTTP request.
        
    Returns:
        IP address string, or "unknown".
    """
    return request.client.host if request.client else "unknown"

def check_rate_limit(ip_address: str, endpoint: str) -> bool:
    """Check if request is within rate limit for given IP and endpoint.
    
    Uses a sliding window counter stored in memory. Different
    endpoints have different limits: /chat is stricter at 10/min
    because it calls the external Gemini API.
    
    Args:
        ip_address: Client IP address string.
        endpoint: Endpoint path string for per-endpoint limits.
        
    Returns:
        True if request is allowed, False if rate limit exceeded.
    """
    now = time.time()
    bucket_key = f"{ip_address}:{endpoint}"
    
    max_requests = CHAT_RATE_LIMIT if endpoint == "chat" else DEFAULT_RATE_LIMIT
    
    if bucket_key not in rate_limit_store:
        rate_limit_store[bucket_key] = []
        
    # Purge old entries
    rate_limit_store[bucket_key] = [
        t for t in rate_limit_store[bucket_key] 
        if now - t < RATE_LIMIT_WINDOW
    ]
    
    if len(rate_limit_store[bucket_key]) >= max_requests:
        logger.warning(
            "rate_limit_exceeded",
            extra={
                "endpoint": f"/api/v1/{endpoint}",
                "request_id": "rate-limit",
                "ip": ip_address,
                "limit": max_requests,
            }
        )
        return False
        
    rate_limit_store[bucket_key].append(now)
    return True

def build_conversation_history(session_id: str) -> List[Dict[str, str]]:
    """Construct conversation history for the Google Gemini API.
    
    Args:
        session_id: Session identifier.
        
    Returns:
        List of dicts representing role and message content.
    """
    if session_id not in sessions:
        sessions[session_id] = []
    return sessions[session_id]

def handle_endpoint_error(
    error: Exception,
    endpoint_name: str,
    request_id: str,
    status_code: int = 500
) -> None:
    """Log error details and raise appropriate HTTP exception.
    
    Centralizes error handling so all endpoints fail the same way:
    full stack trace logged internally, safe generic message
    returned to client to avoid information disclosure.
    
    Args:
        error: The caught exception instance.
        endpoint_name: Name of endpoint for log correlation.
        request_id: Request UUID for log tracing.
        status_code: HTTP status code to return. Defaults to 500.
        
    Raises:
        HTTPException: Always raises with given status_code and
            a safe generic detail message.
    """
    logger.error(
        "endpoint_error",
        extra={
            "endpoint": endpoint_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "request_id": request_id,
        },
        exc_info=True
    )
    raise HTTPException(
        status_code=status_code,
        detail=(
            f"Request processing failed. "
            f"Reference ID: {request_id}"
        )
    )

# =============================================================================
# CARBON CALCULATION ENGINE
# =============================================================================

def calculate_co2(activity_id: str, quantity: float) -> float:
    """Calculate CO2 equivalent for a given activity and quantity.
    
    Uses emission factors from EMISSION_FACTORS constant dict.
    Green actions (tree planting, recycling) return negative values
    representing CO2 offset rather than emission.
    
    Args:
        activity_id: Activity identifier matching EMISSION_FACTORS key.
        quantity: Amount of the activity in the activity's unit.
        
    Returns:
        CO2 equivalent in kilograms. Negative for green actions.
        
    Raises:
        HTTPException: 400 if activity_id is not recognized.
    """
    if activity_id not in EMISSION_FACTORS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown activity ID: {activity_id}"
        )
    return round(quantity * EMISSION_FACTORS[activity_id], 4)

# =============================================================================
# GAMIFICATION ENGINE
# =============================================================================

def award_points(session_id: str, activity_co2_kg: float) -> int:
    """Calculate and award green points for logged activity.
    
    Args:
        session_id: Session identifier.
        activity_co2_kg: CO2 impact in kg.
        
    Returns:
        Points earned for this activity.
    """
    if session_id not in user_points:
        user_points[session_id] = {"points": 0, "badges": []}
    old_points = user_points[session_id]["points"]
    # Why: Use abs() because green actions have negative CO2 values
    # but should still award positive gamification points
    points = max(MIN_ACTIVITY_POINTS, int(abs(activity_co2_kg) * POINTS_PER_CO2_KG))
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
            }
        )
    return points

def check_badges(session_id: str) -> List[str]:
    """Check and award any newly earned badges.
    
    Args:
        session_id: Session identifier.
        
    Returns:
        List of newly earned badge IDs.
    """
    if session_id not in user_points:
        user_points[session_id] = {"points": 0, "badges": []}
    up = user_points[session_id]
    logs = activity_logs.get(session_id, [])
    earned = up["badges"]
    new_badges = []

    total_activities = len(logs)
    total_offset = sum(abs(l["co2_kg"]) for l in logs if l["co2_kg"] < 0)
    green_actions = sum(1 for l in logs if l["co2_kg"] < 0)
    public_transport = sum(1 for l in logs if l["activity"] in ("metro", "bus", "public_transport"))
    trees = sum(1 for l in logs if l["activity"] == "tree_planted")
    recycled_kg = sum(l["quantity"] for l in logs if l["activity"] == "recycled")

    checks = [
        ("first_log", total_activities >= 1),
        ("eco_warrior", green_actions >= 10 and up["points"] >= 100),
        ("carbon_crusher", total_offset >= 50 and up["points"] >= 200),
        ("green_commuter", public_transport >= 5),
        ("tree_hugger", trees >= 3),
        ("recycling_hero", recycled_kg >= 10),
        ("solar_champion", up["points"] >= 500),
        ("planet_protector", up["points"] >= 1000),
        ("net_zero_hero", total_offset >= sum(l["co2_kg"] for l in logs if l["co2_kg"] > 0) and total_activities >= 7),
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
                }
            )

    return new_badges

def get_user_level(points: int) -> str:
    """Determine user gamification level from point total.
    
    Levels progress from Seed through Planet Protector based
    on accumulated green points. Thresholds defined in
    LEVEL_THRESHOLDS constant.
    
    Args:
        points: Total accumulated green points for session.
        
    Returns:
        Level name string matching a key in LEVEL_THRESHOLDS.
    """
    current_level = "Seed"
    for level, threshold in LEVEL_THRESHOLDS.items():
        if points >= threshold:
            current_level = level
    return current_level

# =============================================================================
# CACHE LAYER
# =============================================================================

def get_cached_response(cache_key: str) -> Optional[Any]:
    """Retrieve data from the in-memory cache if it exists and is not expired.
    
    Args:
        cache_key: The cache lookup key.
        
    Returns:
        The cached data, or None if expired or not found.
    """
    entry = _cache.get(cache_key)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL_SECONDS:
        stats["cache_hits"] += 1
        logger.info(
            "cache_hit",
            extra={
                "endpoint": f"/api/v1/{cache_key}",
                "request_id": "cache",
                "cache_key": cache_key,
            }
        )
        return entry["data"]
    
    logger.info(
        "cache_miss",
        extra={
            "endpoint": f"/api/v1/{cache_key}",
            "request_id": "cache",
            "cache_key": cache_key,
        }
    )
    return None

def set_cached_response(cache_key: str, data: Any) -> None:
    """Store data in the in-memory cache with current timestamp.
    
    Args:
        cache_key: The cache key string.
        data: The data to cache.
    """
    _cache[cache_key] = {"data": data, "ts": time.time()}

# =============================================================================
# API ENDPOINTS — CORE
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> Dict[str, str]:
    """Health-check endpoint for Cloud Run.
    
    Args:
        request: The incoming HTTP request.
        
    Returns:
        Dictionary indicating status, app metadata, and version.
    """
    return {
        "status": "ok", 
        "app": APP_NAME, 
        "tagline": APP_TAGLINE, 
        "version": APP_VERSION
    }

@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    """Serve the frontend single-page application.
    
    Args:
        request: The incoming HTTP request.
        
    Returns:
        HTMLResponse containing the index.html content.
    """
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@app.get("/api/v1/about")
async def about(request: Request) -> Dict[str, Any]:
    """Application metadata and mission statement.
    
    Args:
        request: The incoming HTTP request.
        
    Returns:
        Dictionary containing project information and metadata.
    """
    return {
        "app": APP_NAME,
        "tagline": APP_TAGLINE,
        "version": APP_VERSION,
        "live_url": "https://carboncompass-rlzbi2esba-uc.a.run.app/",
        "github": "https://github.com/bikashtiwari603/Carbon-Compass",
        "deployment_region": "us-central1",
        "mission": "Empower every individual to understand measure and reduce their carbon footprint through AI-powered personalized insights and gamified eco-actions",
        "problem_solved": "Most individuals have no idea what their carbon footprint is or how their daily choices contribute to climate change. CarbonCompass bridges this awareness gap with simple tracking personalized AI guidance and actionable reduction roadmaps",
        "target_audience": "Climate-conscious individuals students professionals families anyone wanting to reduce environmental impact",
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

# =============================================================================
# API ENDPOINTS — STATIC DATA
# =============================================================================

@app.get("/api/v1/activities")
async def get_activities(request: Request) -> Response:
    """Return all trackable activity categories with CO2 values.
    
    Args:
        request: The incoming HTTP request.
        
    Returns:
        JSONResponse containing categories list.
    """
    ip_address = get_client_ip(request)
    if not check_rate_limit(ip_address, "activities"):
        # Why: Return Retry-After header so clients can implement
        # proper exponential backoff instead of hammering the API
        return Response(
            content="Rate limit exceeded. Please try again later.",
            status_code=429,
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
        )
        
    data = get_cached_response("activities")
    hit = data is not None
    resp = JSONResponse(content=data if hit else ACTIVITIES_DATA)
    resp.headers["X-Cache"] = "HIT" if hit else "MISS"
    if not hit:
        set_cached_response("activities", ACTIVITIES_DATA)
    return resp

@app.get("/api/v1/badges")
async def get_badges(request: Request) -> Response:
    """Return all available badges.
    
    Args:
        request: The incoming HTTP request.
        
    Returns:
        JSONResponse containing badges list.
    """
    ip_address = get_client_ip(request)
    if not check_rate_limit(ip_address, "badges"):
        # Why: Return Retry-After header so clients can implement
        # proper exponential backoff instead of hammering the API
        return Response(
            content="Rate limit exceeded. Please try again later.",
            status_code=429,
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
        )
        
    data = get_cached_response("badges")
    hit = data is not None
    resp = JSONResponse(content=data if hit else BADGES_DATA)
    resp.headers["X-Cache"] = "HIT" if hit else "MISS"
    if not hit:
        set_cached_response("badges", BADGES_DATA)
    return resp

@app.get("/api/v1/tips")
async def get_tips(request: Request) -> Response:
    """Return daily tips and weekly challenge.
    
    Args:
        request: The incoming HTTP request.
        
    Returns:
        JSONResponse containing daily tips and weekly challenge.
    """
    ip_address = get_client_ip(request)
    if not check_rate_limit(ip_address, "tips"):
        # Why: Return Retry-After header so clients can implement
        # proper exponential backoff instead of hammering the API
        return Response(
            content="Rate limit exceeded. Please try again later.",
            status_code=429,
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
        )
        
    data = get_cached_response("tips")
    hit = data is not None
    resp = JSONResponse(content=data if hit else TIPS_DATA)
    resp.headers["X-Cache"] = "HIT" if hit else "MISS"
    if not hit:
        set_cached_response("tips", TIPS_DATA)
    return resp

@app.get("/api/v1/roadmap")
async def get_roadmap(request: Request) -> Response:
    """Return the 6-phase carbon reduction roadmap.
    
    Args:
        request: The incoming HTTP request.
        
    Returns:
        JSONResponse containing the roadmap dataset.
    """
    ip_address = get_client_ip(request)
    if not check_rate_limit(ip_address, "roadmap"):
        # Why: Return Retry-After header so clients can implement
        # proper exponential backoff instead of hammering the API
        return Response(
            content="Rate limit exceeded. Please try again later.",
            status_code=429,
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
        )
        
    data = get_cached_response("roadmap")
    hit = data is not None
    resp = JSONResponse(content=data if hit else ROADMAP_DATA)
    resp.headers["X-Cache"] = "HIT" if hit else "MISS"
    if not hit:
        set_cached_response("roadmap", ROADMAP_DATA)
    return resp

# =============================================================================
# API ENDPOINTS — USER DATA
# =============================================================================

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> Dict[str, Any]:
    """AI chat endpoint powered by Google Gemini.
    
    Args:
        req: Chat request payload.
        request: The incoming HTTP request.
        
    Returns:
        Dictionary matching the ChatResponse schema.
    """
    request_id = request.state.request_id
    ip_address = get_client_ip(request)
    
    if not check_rate_limit(ip_address, "chat"):
        # Why: Return Retry-After header so clients can implement
        # proper exponential backoff instead of hammering the API
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
        )
        
    validate_session_id(req.session_id)
    message = sanitize_input(req.message)
    
    # Why: Gemini has no built-in memory so we reconstruct the 
    # full conversation on every request using stored history
    history = build_conversation_history(req.session_id)
    
    if req.session_id not in sessions:
        sessions[req.session_id] = []
        stats["total_sessions"] += 1
        
    # Build prompt
    mode_hint = ""
    if req.mode == "quiz":
        mode_hint = "\n[MODE: QUIZ — Ask the user one carbon literacy question and evaluate their answer.]"
    elif req.mode == "calculator":
        mode_hint = "\n[MODE: CALCULATOR — Guide the user step-by-step through calculating their carbon footprint.]"
    elif req.mode == "tips":
        mode_hint = "\n[MODE: TIPS — Provide actionable personalized eco-tips.]"
        
    # Build conversation for Gemini
    conversation_parts = [SYSTEM_PROMPT + mode_hint]
    # Why: Keep context window manageable and focused on the latest turns
    for h in history[-18:]:
        conversation_parts.append(f"{h['role']}: {h['content']}")
    conversation_parts.append(f"User: {message}")
    
    full_prompt = "\n".join(conversation_parts)
    
    ai_text = None
    try:
        logger.info(
            "gemini_api_called",
            extra={
                "endpoint": "/api/v1/chat",
                "request_id": request_id,
                "session_id": req.session_id,
                "session": req.session_id,
            }
        )
        start_time = time.time()
        response = gemini_model.generate_content(full_prompt)
        ai_text = response.text
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(
            "gemini_api_called",
            extra={
                "endpoint": "/api/v1/chat",
                "request_id": request_id,
                "session_id": req.session_id,
                "session": req.session_id,
                "duration_ms": duration_ms,
            }
        )
    except Exception as e:
        logger.error(
            "gemini_api_error",
            extra={
                "endpoint": "/api/v1/chat",
                "request_id": request_id,
                "session_id": req.session_id,
                "session": req.session_id,
                "error_type": type(e).__name__,
            }
        )
        # Fallback models
        for fallback_model_name in ["gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-pro"]:
            try:
                fallback = genai.GenerativeModel(fallback_model_name)
                resp = fallback.generate_content(full_prompt)
                ai_text = resp.text
                break
            except Exception:
                pass
                
        if not ai_text:
            handle_endpoint_error(e, "/api/v1/chat", request_id)
            
    # Update history (max 20 messages)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ai_text})
    
    # Why: Cap history at MAX_SESSION_HISTORY to prevent unbounded 
    # memory growth in long-running Cloud Run instances
    if len(sessions[req.session_id]) > MAX_SESSION_HISTORY:
        sessions[req.session_id] = sessions[req.session_id][-MAX_SESSION_HISTORY:]
        
    stats["total_messages"] += 1
    
    # Points for action words
    points_earned = 0
    msg_lower = message.lower()
    if any(w in msg_lower for w in ACTION_WORDS):
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
                }
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
        }
    )
    
    return {
        "response": ai_text,
        "suggestions": suggestions,
        "points_earned": points_earned,
        "session_id": req.session_id,
    }

@app.post("/api/v1/log-activity", response_model=ActivityLogResponse)
async def log_activity(req: ActivityRequest, request: Request) -> Dict[str, Any]:
    """Log a carbon-emitting or offsetting activity.
    
    Args:
        req: Activity request payload.
        request: The incoming HTTP request.
        
    Returns:
        Dictionary matching the ActivityLogResponse schema.
    """
    request_id = request.state.request_id
    ip_address = get_client_ip(request)
    
    if not check_rate_limit(ip_address, "log-activity"):
        # Why: Return Retry-After header so clients can implement
        # proper exponential backoff instead of hammering the API
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
        )
        
    try:
        validate_session_id(req.session_id)
        sanitize_input(req.activity)
        sanitize_input(req.category)
        
        co2_kg = calculate_co2(req.activity, req.quantity)
        
        if req.session_id not in activity_logs:
            activity_logs[req.session_id] = []
            
        activity_logs[req.session_id].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": req.category,
            "activity": req.activity,
            "quantity": req.quantity,
            "unit": req.unit,
            "co2_kg": co2_kg,
        })
        
        points_earned = award_points(req.session_id, co2_kg)
        stats["total_activities_logged"] += 1
        
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
            }
        )
        
        return {
            "co2_kg": co2_kg,
            "points_earned": points_earned,
            "total_points": user_points[req.session_id]["points"],
            "message": f"{'🌱 Great green action!' if co2_kg < 0 else '📝 Activity logged!'} {abs(co2_kg):.2f}kg CO2 {direction}",
            "new_badges": new_badges,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        handle_endpoint_error(e, "/api/v1/log-activity", request_id)

@app.get("/api/v1/dashboard/{session_id}")
async def get_dashboard(session_id: str, request: Request) -> Dict[str, Any]:
    """Return comprehensive dashboard data for a session.
    
    Args:
        session_id: Session identifier.
        request: The incoming HTTP request.
        
    Returns:
        Dictionary containing session totals, trends, level, and achievements.
    """
    request_id = request.state.request_id
    ip_address = get_client_ip(request)
    
    if not check_rate_limit(ip_address, "dashboard"):
        # Why: Return Retry-After header so clients can implement
        # proper exponential backoff instead of hammering the API
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
        )
        
    try:
        validate_session_id(session_id)
        logs = activity_logs.get(session_id, [])
        
        total_co2_kg = round(sum(l["co2_kg"] for l in logs if l["co2_kg"] > 0), 2)
        total_offset_kg = round(abs(sum(l["co2_kg"] for l in logs if l["co2_kg"] < 0)), 2)
        net_co2_kg = round(total_co2_kg - total_offset_kg, 2)
        
        breakdown: Dict[str, float] = {}
        for l in logs:
            cat = l["category"]
            breakdown[cat] = round(breakdown.get(cat, 0) + l["co2_kg"], 2)
            
        if logs:
            dates = set()
            for l in logs:
                try:
                    dates.add(l["timestamp"][:10])
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
            day_total = round(sum(l["co2_kg"] for l in logs if l["timestamp"][:10] == d), 2)
            trend.append({"date": d, "co2_kg": day_total})
            
        positive_breakdown = {k: v for k, v in breakdown.items() if v > 0}
        top_emission_source = max(positive_breakdown, key=positive_breakdown.get) if positive_breakdown else "none"
        
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
        handle_endpoint_error(e, f"/api/v1/dashboard/{session_id}", request_id)

@app.get("/api/v1/stats", response_model=StatsResponse)
async def get_stats(request: Request) -> Dict[str, Any]:
    """Global application usage statistics.
    
    Args:
        request: The incoming HTTP request.
        
    Returns:
        Dictionary matching the StatsResponse schema.
    """
    request_id = request.state.request_id
    ip_address = get_client_ip(request)
    
    if not check_rate_limit(ip_address, "stats"):
        # Why: Return Retry-After header so clients can implement
        # proper exponential backoff instead of hammering the API
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
        )
        
    try:
        return {
            "total_sessions": stats["total_sessions"],
            "total_messages": stats["total_messages"],
            "total_activities_logged": stats["total_activities_logged"],
            "uptime_seconds": round(time.time() - app_start_time, 2),
            "cache_hits": stats["cache_hits"],
        }
    except Exception as e:
        handle_endpoint_error(e, "/api/v1/stats", request_id)

@app.get("/api/v1/weekly-report/{session_id}")
async def weekly_report(session_id: str, request: Request) -> Dict[str, Any]:
    """Generate a comprehensive weekly CO2 report.
    
    Args:
        session_id: Session identifier.
        request: The incoming HTTP request.
        
    Returns:
        Dictionary containing weekly summaries, averages, and eco tips.
    """
    request_id = request.state.request_id
    ip_address = get_client_ip(request)
    
    if not check_rate_limit(ip_address, "weekly-report"):
        # Why: Return Retry-After header so clients can implement
        # proper exponential backoff instead of hammering the API
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
        )
        
    try:
        validate_session_id(session_id)
        logs = activity_logs.get(session_id, [])
        
        total_co2 = round(sum(l["co2_kg"] for l in logs if l["co2_kg"] > 0), 2)
        total_offset = round(abs(sum(l["co2_kg"] for l in logs if l["co2_kg"] < 0)), 2)
        net = round(total_co2 - total_offset, 2)
        
        daily: Dict[str, float] = {}
        for l in logs:
            d = l["timestamp"][:10]
            daily[d] = round(daily.get(d, 0) + l["co2_kg"], 2)
            
        best_day = min(daily, key=daily.get) if daily else "N/A"
        worst_day = max(daily, key=daily.get) if daily else "N/A"
        
        india_weekly_avg = round(1900 / 52, 2)
        saved_vs_avg = round(india_weekly_avg - net, 2)
        
        cat_totals: Dict[str, float] = {}
        for l in logs:
            if l["co2_kg"] > 0:
                cat_totals[l["category"]] = round(cat_totals.get(l["category"], 0) + l["co2_kg"], 2)
                
        sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
        improvement_tips = []
        tip_map = {
            "transport": "Try using public transport or cycling for short trips to cut transport emissions.",
            "food": "Consider one more plant-based meal per day to reduce food-related CO2.",
            "home": "Audit your electricity usage — switch to 5-star appliances and LED lighting.",
            "shopping": "Buy fewer new items and consider second-hand or refurbished products.",
        }
        for cat, _ in sorted_cats[:3]:
            improvement_tips.append(tip_map.get(cat, "Keep tracking and reducing your footprint! 🌱"))
            
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
            "improvement_tips": improvement_tips if improvement_tips else ["Start logging activities to get personalised tips! 🌱"],
            "india_weekly_avg_kg": india_weekly_avg,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        handle_endpoint_error(e, f"/api/v1/weekly-report/{session_id}", request_id)

@app.post("/api/v1/profile", response_model=ProfileResponse)
async def set_profile(req: ProfileRequest, request: Request) -> Dict[str, Any]:
    """Set user profile and return personalised baseline estimate.
    
    Args:
        req: Profile request payload.
        request: The incoming HTTP request.
        
    Returns:
        Dictionary matching the ProfileResponse schema.
    """
    request_id = request.state.request_id
    ip_address = get_client_ip(request)
    
    if not check_rate_limit(ip_address, "profile"):
        # Why: Return Retry-After header so clients can implement
        # proper exponential backoff instead of hammering the API
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
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
        
        # Baseline calculation
        base = INDIA_AVERAGE_ANNUAL_TONNES
        
        # Diet adjustments
        diet_adj = {"vegan": -0.30, "vegetarian": -0.15, "omnivore": 0, "heavy_meat": 0.20, "meat": 0.20}
        base *= 1 + diet_adj.get(req.diet.lower().replace(" ", "_"), 0)
        
        # Transport adjustments
        transport_adj = {"metro": -0.20, "bus": -0.15, "car": 0.30, "motorcycle": 0.15, "cycle": -0.40, "walk": -0.40}
        base *= 1 + transport_adj.get(req.transport.lower().replace(" ", "_"), 0)
        
        # Home energy adjustments
        energy_adj = {"solar": -0.25, "normal_grid": 0, "heavy_ac": 0.15, "normal": 0}
        base *= 1 + energy_adj.get(req.home_energy.lower().replace(" ", "_"), 0)
        
        base = round(base, 2)
        
        vs_india = "below" if base < INDIA_AVERAGE_ANNUAL_TONNES else ("above" if base > INDIA_AVERAGE_ANNUAL_TONNES else "at")
        vs_global = "below" if base < GLOBAL_AVERAGE_ANNUAL_TONNES else "above"
        
        # Top opportunity
        opportunities = {
            "heavy_meat": "Switch to a more plant-based diet",
            "meat": "Switch to a more plant-based diet",
            "car": "Switch to public transport or cycling",
            "motorcycle": "Consider public transport for daily commute",
            "heavy_ac": "Optimize AC usage and consider solar",
        }
        top_opp = "Keep up your green habits! 🌱"
        for key, suggestion in opportunities.items():
            if key in (req.diet.lower() + req.transport.lower() + req.home_energy.lower()).replace(" ", "_"):
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
        handle_endpoint_error(e, "/api/v1/profile", request_id)

@app.on_event("shutdown")
def shutdown_event() -> None:
    """Handle application shutdown and log uptime statistics.
    
    Returns:
        None.
    """
    uptime_seconds = round(time.time() - app_start_time, 2)
    logger.info(
        "app_shutdown",
        extra={
            "endpoint": "shutdown",
            "request_id": "shutdown",
            "uptime_seconds": uptime_seconds,
        }
    )

# =============================================================================
# STATIC FILE SERVING
# =============================================================================
# Note: Static files are served via the GET "/" root endpoint
# and the frontend HTML resides in static/index.html.
