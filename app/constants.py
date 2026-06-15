"""Constants and static datasets for CarbonCompass."""

import re
from typing import Any, Dict, List, Set

# Carbon emission factors (kg CO2 per unit)
EMISSION_FACTORS: Dict[str, float] = {
    "car_petrol": 0.21,  # kg CO2 per km
    "car_diesel": 0.17,  # kg CO2 per km
    "motorcycle": 0.11,  # kg CO2 per km
    "bus": 0.089,  # kg CO2 per km
    "metro": 0.041,  # kg CO2 per km
    "flight_domestic": 0.255,  # kg CO2 per km per passenger
    "flight_international": 0.195,  # kg CO2 per km per passenger
    "electricity": 0.82,  # kg CO2 per kWh (India grid CEF)
    "lpg": 2.98,  # kg CO2 per kg
    "cng": 2.79,  # kg CO2 per kg
    "beef": 27.0,  # kg CO2 per kg food
    "chicken": 6.9,  # kg CO2 per kg food
    "fish": 5.4,  # kg CO2 per kg food
    "vegetables": 2.0,  # kg CO2 per kg food
    "dairy": 3.2,  # kg CO2 per kg food
    "clothing": 10.0,  # kg CO2 per item
    "electronics": 70.0,  # kg CO2 per item
    "appliances": 200.0,  # kg CO2 per item
    "tree_planted": -21.0,  # kg CO2 absorbed per year
    "recycled": -0.5,  # kg CO2 saved per kg recycled
    "composted": -0.5,  # kg CO2 saved per kg composted
    "public_transport": -2.5,  # kg CO2 saved per trip vs car
}

# India carbon benchmarks (tonnes CO2 per year)
INDIA_AVERAGE_ANNUAL_TONNES: float = 1.9
GLOBAL_AVERAGE_ANNUAL_TONNES: float = 4.8
PARIS_TARGET_ANNUAL_TONNES: float = 2.0

# Rate limiting configuration
CHAT_RATE_LIMIT: int = 10  # requests per minute for /chat
DEFAULT_RATE_LIMIT: int = 60  # requests per minute for other endpoints
RATE_LIMIT_WINDOW: int = 60  # window size in seconds

# Session and input limits
MAX_SESSION_HISTORY: int = 20  # maximum messages stored per session
MAX_MESSAGE_LENGTH: int = 2000  # maximum user message character length
MIN_MESSAGE_LENGTH: int = 1  # minimum user message character length
MAX_SESSION_ID_LENGTH: int = 100  # maximum session ID character length
MAX_REPEAT_CHARS: int = 100  # max consecutive repeated characters allowed

# Cache configuration
CACHE_TTL_SECONDS: int = 300  # 5 minutes cache TTL for static endpoints

# Gamification thresholds
POINTS_PER_CO2_KG: int = 10  # green points awarded per kg CO2 unit
MIN_ACTIVITY_POINTS: int = 5  # minimum points per logged activity
TIP_COMPLETION_POINTS: int = 25  # points for completing a daily tip
QUIZ_CORRECT_POINTS: int = 10  # points per correct quiz answer

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
SESSION_ID_PATTERN: re.Pattern = re.compile(r"^[a-zA-Z0-9_-]+$")

# Action words for chat points
ACTION_WORDS: Set[str] = {
    "planted",
    "switched",
    "reduced",
    "recycled",
    "composted",
    "walked",
    "cycled",
    "saved",
}

# Static Datasets
ACTIVITIES_DATA: Dict[str, Any] = {
    "categories": [
        {
            "id": "transport",
            "name": "Transport 🚗",
            "color": "#FF6B6B",
            "icon": "🚗",
            "activities": [
                {
                    "id": "car_petrol",
                    "name": "Car (Petrol)",
                    "unit": "km",
                    "co2_per_unit": 0.21,
                    "icon": "🚗",
                },
                {
                    "id": "car_diesel",
                    "name": "Car (Diesel)",
                    "unit": "km",
                    "co2_per_unit": 0.17,
                    "icon": "🚙",
                },
                {
                    "id": "motorcycle",
                    "name": "Motorcycle",
                    "unit": "km",
                    "co2_per_unit": 0.11,
                    "icon": "🏍️",
                },
                {
                    "id": "bus",
                    "name": "Bus",
                    "unit": "km",
                    "co2_per_unit": 0.089,
                    "icon": "🚌",
                },
                {
                    "id": "metro",
                    "name": "Metro/Train",
                    "unit": "km",
                    "co2_per_unit": 0.041,
                    "icon": "🚇",
                },
                {
                    "id": "flight_domestic",
                    "name": "Domestic Flight",
                    "unit": "km",
                    "co2_per_unit": 0.255,
                    "icon": "✈️",
                },
                {
                    "id": "flight_international",
                    "name": "International Flight",
                    "unit": "km",
                    "co2_per_unit": 0.195,
                    "icon": "🌍",
                },
            ],
        },
        {
            "id": "home",
            "name": "Home Energy 🏠",
            "color": "#4ECDC4",
            "icon": "🏠",
            "activities": [
                {
                    "id": "electricity",
                    "name": "Electricity",
                    "unit": "kWh",
                    "co2_per_unit": 0.82,
                    "icon": "⚡",
                },
                {
                    "id": "lpg",
                    "name": "LPG Cooking Gas",
                    "unit": "kg",
                    "co2_per_unit": 2.98,
                    "icon": "🔥",
                },
                {
                    "id": "cng",
                    "name": "CNG",
                    "unit": "kg",
                    "co2_per_unit": 2.79,
                    "icon": "⛽",
                },
            ],
        },
        {
            "id": "food",
            "name": "Food 🍽️",
            "color": "#45B7D1",
            "icon": "🍽️",
            "activities": [
                {
                    "id": "beef",
                    "name": "Beef",
                    "unit": "kg",
                    "co2_per_unit": 27.0,
                    "icon": "🥩",
                },
                {
                    "id": "chicken",
                    "name": "Chicken",
                    "unit": "kg",
                    "co2_per_unit": 6.9,
                    "icon": "🍗",
                },
                {
                    "id": "fish",
                    "name": "Fish",
                    "unit": "kg",
                    "co2_per_unit": 5.4,
                    "icon": "🐟",
                },
                {
                    "id": "vegetables",
                    "name": "Vegetables",
                    "unit": "kg",
                    "co2_per_unit": 2.0,
                    "icon": "🥦",
                },
                {
                    "id": "dairy",
                    "name": "Dairy Products",
                    "unit": "kg",
                    "co2_per_unit": 3.2,
                    "icon": "🥛",
                },
            ],
        },
        {
            "id": "shopping",
            "name": "Shopping 🛍️",
            "color": "#96CEB4",
            "icon": "🛍️",
            "activities": [
                {
                    "id": "clothing",
                    "name": "Clothing",
                    "unit": "item",
                    "co2_per_unit": 10.0,
                    "icon": "👕",
                },
                {
                    "id": "electronics",
                    "name": "Electronics",
                    "unit": "item",
                    "co2_per_unit": 70.0,
                    "icon": "📱",
                },
                {
                    "id": "appliances",
                    "name": "Appliances",
                    "unit": "item",
                    "co2_per_unit": 200.0,
                    "icon": "🏠",
                },
            ],
        },
        {
            "id": "green_actions",
            "name": "Green Actions 🌱",
            "color": "var(--accent-green)",
            "icon": "🌱",
            "activities": [
                {
                    "id": "tree_planted",
                    "name": "Tree Planted",
                    "unit": "tree",
                    "co2_per_unit": -21.0,
                    "icon": "🌳",
                },
                {
                    "id": "recycled",
                    "name": "Recycling",
                    "unit": "kg",
                    "co2_per_unit": -0.5,
                    "icon": "♻️",
                },
                {
                    "id": "composted",
                    "name": "Composting",
                    "unit": "kg",
                    "co2_per_unit": -0.5,
                    "icon": "🌿",
                },
                {
                    "id": "public_transport",
                    "name": "Chose Public Transport instead of Car",
                    "unit": "trip",
                    "co2_per_unit": -2.5,
                    "icon": "🚌",
                },
            ],
        },
    ]
}

BADGES_DATA: List[Dict[str, Any]] = [
    {
        "id": "first_log",
        "name": "First Step 🌱",
        "description": "Log your first activity",
        "points_required": 0,
        "activities_required": 1,
        "icon": "🌱",
        "color": "var(--accent-green)",
    },
    {
        "id": "eco_warrior",
        "name": "Eco Warrior ⚔️",
        "description": "Log 10 green actions",
        "points_required": 100,
        "activities_required": 10,
        "icon": "⚔️",
        "color": "#4ECDC4",
    },
    {
        "id": "carbon_crusher",
        "name": "Carbon Crusher 💪",
        "description": "Offset 50kg of CO2",
        "points_required": 200,
        "activities_required": 0,
        "icon": "💪",
        "color": "#45B7D1",
    },
    {
        "id": "green_commuter",
        "name": "Green Commuter 🚇",
        "description": "Log 5 public transport trips",
        "points_required": 0,
        "activities_required": 5,
        "icon": "🚇",
        "color": "#96CEB4",
    },
    {
        "id": "tree_hugger",
        "name": "Tree Hugger 🌳",
        "description": "Plant 3 trees",
        "points_required": 0,
        "activities_required": 3,
        "icon": "🌳",
        "color": "var(--accent-green)",
    },
    {
        "id": "recycling_hero",
        "name": "Recycling Hero ♻️",
        "description": "Recycle 10kg of waste",
        "points_required": 0,
        "activities_required": 0,
        "icon": "♻️",
        "color": "#FF6B6B",
    },
    {
        "id": "solar_champion",
        "name": "Solar Champion ☀️",
        "description": "Earn 500 green points",
        "points_required": 500,
        "activities_required": 0,
        "icon": "☀️",
        "color": "#FFD700",
    },
    {
        "id": "planet_protector",
        "name": "Planet Protector 🌍",
        "description": "Earn 1000 green points",
        "points_required": 1000,
        "activities_required": 0,
        "icon": "🌍",
        "color": "#FF6B00",
    },
    {
        "id": "net_zero_hero",
        "name": "Net Zero Hero 🏆",
        "description": "Achieve net zero for a week",
        "points_required": 0,
        "activities_required": 0,
        "icon": "🏆",
        "color": "#f4d03f",
    },
]

TIPS_DATA: Dict[str, Any] = {
    "daily_tips": [
        {
            "id": 1,
            "category": "transport",
            "tip": (
                "Take the metro instead of driving today "
                "— saves 0.8kg CO2 for a 5km trip"
            ),
            "impact": "Low",
            "savings_co2_kg": 0.8,
            "icon": "🚇",
        },
        {
            "id": 2,
            "category": "food",
            "tip": (
                "Try one plant-based meal today "
                "— even one meatless meal saves 1.5kg CO2"
            ),
            "impact": "Medium",
            "savings_co2_kg": 1.5,
            "icon": "🥗",
        },
        {
            "id": 3,
            "category": "home",
            "tip": (
                "Switch off lights and fans when leaving a room "
                "— saves up to 0.5kWh daily"
            ),
            "impact": "Low",
            "savings_co2_kg": 0.4,
            "icon": "💡",
        },
        {
            "id": 4,
            "category": "shopping",
            "tip": (
                "Carry a reusable bag today "
                "— plastic bags take 500 years to decompose"
            ),
            "impact": "Low",
            "savings_co2_kg": 0.1,
            "icon": "🛍️",
        },
        {
            "id": 5,
            "category": "green",
            "tip": (
                "Start a small compost bin "
                "— diverts food waste from landfill producing methane"
            ),
            "impact": "Medium",
            "savings_co2_kg": 0.5,
            "icon": "🌿",
        },
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
            "actions": [
                "Log all daily activities for 7 days",
                "Complete carbon footprint quiz",
                "Identify your top 3 emission sources",
                "Set your reduction goal",
            ],
            "milestone": "Know your baseline CO2 number",
        },
        {
            "phase": 2,
            "title": "Quick Wins 🎯",
            "duration": "Week 2-3",
            "description": "Make easy low-effort changes with immediate impact",
            "color": "#FF8E53",
            "actions": [
                "Switch to LED bulbs",
                "Carry reusable bags and bottles",
                "Reduce one meat meal per week",
                "Unplug devices not in use",
            ],
            "milestone": "Reduce footprint by 10%",
        },
        {
            "phase": 3,
            "title": "Transport Shift 🚇",
            "duration": "Month 2",
            "description": "Transform how you move — biggest impact category",
            "color": "#4ECDC4",
            "actions": [
                "Use public transport for work commute",
                "Walk or cycle for trips under 2km",
                "Combine errands into single trips",
                "Consider carpooling",
            ],
            "milestone": "Reduce transport emissions by 30%",
        },
        {
            "phase": 4,
            "title": "Home Green 🏠",
            "duration": "Month 3",
            "description": "Make your home more energy efficient",
            "color": "#45B7D1",
            "actions": [
                "Audit home electricity consumption",
                "Install energy efficient appliances",
                "Optimize AC usage to 24 degrees",
                "Explore rooftop solar under PM Surya Ghar scheme",
            ],
            "milestone": "Reduce home energy emissions by 25%",
        },
        {
            "phase": 5,
            "title": "Food and Lifestyle 🥗",
            "duration": "Month 4",
            "description": "Transform diet and consumption habits",
            "color": "#96CEB4",
            "actions": [
                "Adopt flexitarian diet reducing meat by 50%",
                "Buy local and seasonal produce",
                "Start home composting",
                "Reduce food waste with meal planning",
            ],
            "milestone": "Reduce food footprint by 40%",
        },
        {
            "phase": 6,
            "title": "Carbon Champion 🏆",
            "duration": "Month 5-6",
            "description": "Offset remaining emissions and inspire others",
            "color": "var(--accent-green)",
            "actions": [
                "Plant trees through verified programs",
                "Calculate and offset remaining footprint",
                "Share your journey on social media",
                "Join local environmental groups",
            ],
            "milestone": "Achieve net zero lifestyle",
        },
    ]
}

_CO2_LOOKUP: Dict[str, float] = {}
for cat in ACTIVITIES_DATA["categories"]:
    for act in cat["activities"]:
        _CO2_LOOKUP[act["id"]] = act["co2_per_unit"]
