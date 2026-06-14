"""
CarbonCompass — AI-Powered Carbon Footprint Tracking Application
Backend API powered by FastAPI and Google Gemini AI.
Navigate Towards a Greener Future.
"""

import os
import re
import time
import uuid
import random
import logging
import unicodedata
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Environment & Gemini setup
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here" or len(GEMINI_API_KEY) < 10:
    logging.warning(
        "GEMINI_API_KEY is missing, placeholder, or too short. "
        "AI chat will not work until a valid key is provided."
    )

import google.generativeai as genai  # noqa: E402

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# ---------------------------------------------------------------------------
# Cloud Logging (falls back to standard logging)
# ---------------------------------------------------------------------------

try:
    import google.cloud.logging as cloud_logging
    cloud_client = cloud_logging.Client()
    cloud_client.setup_logging()
    logger = logging.getLogger("carboncompass")
    logger.info("Google Cloud Logging initialised.")
except Exception:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("carboncompass")
    logger.info("Falling back to standard logging.")

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app_start_time: float = time.time()

app = FastAPI(
    title="CarbonCompass",
    description="Navigate Towards a Greener Future — AI-powered carbon footprint tracker",
    version="1.0.0",
)

startup_ms = round((time.time() - app_start_time) * 1000, 2)
logger.info(f"CarbonCompass started in {startup_ms}ms")

# ---------------------------------------------------------------------------
# Middleware — order matters (outermost first in code = outermost in stack)
# ---------------------------------------------------------------------------

# 1. GZip
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 2. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# 3. Security headers
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
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


# 4. Request-ID
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Rate limiting (in-memory, per IP)
# ---------------------------------------------------------------------------

rate_limit_store: dict = {}  # ip -> {endpoint_key: [(timestamp, ...)]}


def _rate_limit(request: Request, key: str, max_requests: int, window: int = 60):
    """Check and enforce rate limit. Raises 429 if exceeded."""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket_key = f"{ip}:{key}"

    if bucket_key not in rate_limit_store:
        rate_limit_store[bucket_key] = []

    # Purge old entries
    rate_limit_store[bucket_key] = [t for t in rate_limit_store[bucket_key] if now - t < window]

    if len(rate_limit_store[bucket_key]) >= max_requests:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(window)},
        )

    rate_limit_store[bucket_key].append(now)


# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------

_cache: dict = {}  # key -> {"data": ..., "ts": float}
CACHE_TTL = 300  # seconds


def cache_get(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL:
        stats["cache_hits"] += 1
        return entry["data"], True
    return None, False


def cache_set(key: str, data):
    _cache[key] = {"data": data, "ts": time.time()}


# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------

sessions: dict = {}          # session_id -> [messages]
user_profiles: dict = {}     # session_id -> profile dict
user_points: dict = {}       # session_id -> {"points": int, "badges": []}
activity_logs: dict = {}     # session_id -> [activity dicts]
stats: dict = {
    "total_sessions": 0,
    "total_messages": 0,
    "total_activities_logged": 0,
    "cache_hits": 0,
}

# ---------------------------------------------------------------------------
# Input sanitisation
# ---------------------------------------------------------------------------

_SESSION_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def sanitize_input(text: str) -> str:
    """Strip dangerous content from user input."""
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
    # Normalize unicode
    text = unicodedata.normalize("NFKC", text)
    return text.strip()


def validate_session_id(session_id: str):
    if not _SESSION_RE.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID format.")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Static data
# ---------------------------------------------------------------------------

ACTIVITIES_DATA = {
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

BADGES_DATA = [
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

TIPS_DATA = {
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

ROADMAP_DATA = {
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

# CO2 lookup for activity logging
_CO2_LOOKUP: dict = {}
for cat in ACTIVITIES_DATA["categories"]:
    for act in cat["activities"]:
        _CO2_LOOKUP[act["id"]] = act["co2_per_unit"]


# ---------------------------------------------------------------------------
# Gemini system prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are CarbonCompass AI, a friendly expert sustainability assistant with the mission Navigate Towards a Greener Future. You help individuals understand track and reduce their carbon footprint.

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

# Action words that earn bonus points
ACTION_WORDS = {"planted", "switched", "reduced", "recycled", "composted", "walked", "cycled", "saved"}

# ---------------------------------------------------------------------------
# Helper: badge checking
# ---------------------------------------------------------------------------


def _check_badges(session_id: str) -> list:
    """Check and award any newly earned badges. Returns list of new badge names."""
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

    return new_badges


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """Health-check endpoint for Cloud Run."""
    return {"status": "ok", "app": "CarbonCompass", "tagline": "Navigate Towards a Greener Future", "version": "1.0.0"}


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend single-page application."""
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.get("/api/v1/about")
async def about():
    """Application metadata and mission statement."""
    return {
        "app": "CarbonCompass",
        "tagline": "Navigate Towards a Greener Future",
        "version": "1.0.0",
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



@app.get("/api/v1/stats")
async def get_stats():
    """Global application usage statistics."""
    return {
        "total_sessions": stats["total_sessions"],
        "total_messages": stats["total_messages"],
        "total_activities_logged": stats["total_activities_logged"],
        "uptime_seconds": round(time.time() - app_start_time, 2),
        "cache_hits": stats["cache_hits"],
    }


# ---- Chat ------------------------------------------------------------------

@app.post("/api/v1/chat")
async def chat(req: ChatRequest, request: Request):
    """AI chat endpoint powered by Google Gemini."""
    _rate_limit(request, "chat", max_requests=10)

    validate_session_id(req.session_id)
    message = sanitize_input(req.message)

    # Session tracking
    if req.session_id not in sessions:
        sessions[req.session_id] = []
        stats["total_sessions"] += 1

    history = sessions[req.session_id]

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
    for h in history[-18:]:  # keep context window manageable
        conversation_parts.append(f"{h['role']}: {h['content']}")
    conversation_parts.append(f"User: {message}")

    full_prompt = "\n".join(conversation_parts)

    try:
        response = gemini_model.generate_content(full_prompt)
        ai_text = response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        ai_text = "I'm having trouble connecting to my AI brain right now. 🌱 Please try again in a moment!"

    # Update history (max 20 messages)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ai_text})
    if len(history) > 20:
        history[:] = history[-20:]

    stats["total_messages"] += 1

    # Points for action words
    points_earned = 0
    msg_lower = message.lower()
    if any(w in msg_lower for w in ACTION_WORDS):
        points_earned = random.randint(5, 15)
        if req.session_id not in user_points:
            user_points[req.session_id] = {"points": 0, "badges": []}
        user_points[req.session_id]["points"] += points_earned

    # Generate suggestions
    suggestions = [
        "How can I reduce my transport emissions? 🚇",
        "What's my estimated carbon footprint? 🧮",
        "Give me today's eco-tip 🌱",
    ]

    logger.info(f"Chat session={req.session_id} mode={req.mode} msg_len={len(message)}")

    return {
        "response": ai_text,
        "suggestions": suggestions,
        "points_earned": points_earned,
        "session_id": req.session_id,
    }


# ---- Activities ------------------------------------------------------------

@app.get("/api/v1/activities")
async def get_activities(request: Request):
    """Return all trackable activity categories with CO2 values."""
    _rate_limit(request, "activities", max_requests=60)
    data, hit = cache_get("activities")
    resp = JSONResponse(content=data if hit else ACTIVITIES_DATA)
    resp.headers["X-Cache"] = "HIT" if hit else "MISS"
    if not hit:
        cache_set("activities", ACTIVITIES_DATA)
    return resp


# ---- Log Activity ----------------------------------------------------------

@app.post("/api/v1/log-activity")
async def log_activity(req: ActivityRequest, request: Request):
    """Log a carbon-emitting or offsetting activity."""
    _rate_limit(request, "log-activity", max_requests=60)

    validate_session_id(req.session_id)
    sanitize_input(req.activity)
    sanitize_input(req.category)

    co2_per_unit = _CO2_LOOKUP.get(req.activity, 0)
    co2_kg = round(req.quantity * co2_per_unit, 4)

    if req.session_id not in activity_logs:
        activity_logs[req.session_id] = []
    if req.session_id not in user_points:
        user_points[req.session_id] = {"points": 0, "badges": []}

    activity_logs[req.session_id].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "category": req.category,
        "activity": req.activity,
        "quantity": req.quantity,
        "unit": req.unit,
        "co2_kg": co2_kg,
    })

    # Points
    points_earned = max(5, round(abs(co2_kg) * 10))
    user_points[req.session_id]["points"] += points_earned

    stats["total_activities_logged"] += 1

    # Badge check
    new_badges = _check_badges(req.session_id)

    direction = "offset" if co2_kg < 0 else "emitted"
    logger.info(f"Activity logged session={req.session_id} activity={req.activity} co2={co2_kg}kg {direction}")

    return {
        "co2_kg": co2_kg,
        "points_earned": points_earned,
        "total_points": user_points[req.session_id]["points"],
        "message": f"{'🌱 Great green action!' if co2_kg < 0 else '📝 Activity logged!'} {abs(co2_kg):.2f}kg CO2 {direction}",
        "new_badges": new_badges,
    }


# ---- Dashboard -------------------------------------------------------------

@app.get("/api/v1/dashboard/{session_id}")
async def get_dashboard(session_id: str, request: Request):
    """Return comprehensive dashboard data for a session."""
    _rate_limit(request, "dashboard", max_requests=60)

    logs = activity_logs.get(session_id, [])

    total_co2_kg = round(sum(l["co2_kg"] for l in logs if l["co2_kg"] > 0), 2)
    total_offset_kg = round(abs(sum(l["co2_kg"] for l in logs if l["co2_kg"] < 0)), 2)
    net_co2_kg = round(total_co2_kg - total_offset_kg, 2)

    # Breakdown by category
    breakdown: dict = {}
    for l in logs:
        cat = l["category"]
        breakdown[cat] = round(breakdown.get(cat, 0) + l["co2_kg"], 2)

    # Days active
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

    # Annualised comparisons
    annual_estimate = daily_average * 365 / 1000  # tonnes
    comparison_india = round(annual_estimate - 1.9, 2)
    comparison_global = round(annual_estimate - 4.8, 2)

    # Trend: last 7 days
    trend = []
    today = datetime.now(timezone.utc).date()
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        day_total = round(sum(l["co2_kg"] for l in logs if l["timestamp"][:10] == d), 2)
        trend.append({"date": d, "co2_kg": day_total})

    # Top emission source
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


# ---- Badges ----------------------------------------------------------------

@app.get("/api/v1/badges")
async def get_badges(request: Request):
    """Return all available badges."""
    _rate_limit(request, "badges", max_requests=60)
    data, hit = cache_get("badges")
    resp = JSONResponse(content=data if hit else BADGES_DATA)
    resp.headers["X-Cache"] = "HIT" if hit else "MISS"
    if not hit:
        cache_set("badges", BADGES_DATA)
    return resp


# ---- Tips ------------------------------------------------------------------

@app.get("/api/v1/tips")
async def get_tips(request: Request):
    """Return daily tips and weekly challenge."""
    _rate_limit(request, "tips", max_requests=60)
    data, hit = cache_get("tips")
    resp = JSONResponse(content=data if hit else TIPS_DATA)
    resp.headers["X-Cache"] = "HIT" if hit else "MISS"
    if not hit:
        cache_set("tips", TIPS_DATA)
    return resp


# ---- Roadmap ---------------------------------------------------------------

@app.get("/api/v1/roadmap")
async def get_roadmap(request: Request):
    """Return the 6-phase carbon reduction roadmap."""
    _rate_limit(request, "roadmap", max_requests=60)
    data, hit = cache_get("roadmap")
    resp = JSONResponse(content=data if hit else ROADMAP_DATA)
    resp.headers["X-Cache"] = "HIT" if hit else "MISS"
    if not hit:
        cache_set("roadmap", ROADMAP_DATA)
    return resp


# ---- Weekly Report ---------------------------------------------------------

@app.get("/api/v1/weekly-report/{session_id}")
async def weekly_report(session_id: str, request: Request):
    """Generate a comprehensive weekly CO2 report."""
    _rate_limit(request, "weekly-report", max_requests=60)
    logs = activity_logs.get(session_id, [])

    total_co2 = round(sum(l["co2_kg"] for l in logs if l["co2_kg"] > 0), 2)
    total_offset = round(abs(sum(l["co2_kg"] for l in logs if l["co2_kg"] < 0)), 2)
    net = round(total_co2 - total_offset, 2)

    # Daily breakdown
    daily: dict = {}
    for l in logs:
        d = l["timestamp"][:10]
        daily[d] = round(daily.get(d, 0) + l["co2_kg"], 2)

    best_day = min(daily, key=daily.get) if daily else "N/A"
    worst_day = max(daily, key=daily.get) if daily else "N/A"

    # India average comparison (weekly portion)
    india_weekly_avg = round(1900 / 52, 2)  # ~36.5 kg
    saved_vs_avg = round(india_weekly_avg - net, 2)

    # Top categories
    cat_totals: dict = {}
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


# ---- Profile ---------------------------------------------------------------

@app.post("/api/v1/profile")
async def set_profile(req: ProfileRequest, request: Request):
    """Set user profile and return personalised baseline estimate."""
    _rate_limit(request, "profile", max_requests=60)

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
    base = 1.9  # India average tonnes/year

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

    vs_india = "below" if base < 1.9 else ("above" if base > 1.9 else "at")
    vs_global = "below" if base < 4.8 else "above"

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

    logger.info(f"Profile set session={req.session_id} estimate={base}T/year")

    return {
        "estimated_annual_co2_tonnes": base,
        "vs_india_average": f"{vs_india} India average (1.9T)",
        "vs_global_average": f"{vs_global} global average (4.8T)",
        "top_reduction_opportunity": top_opp,
    }
