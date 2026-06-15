"""CarbonCompass — Navigate Towards a Greener Future.

Entry point for the FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.logging_setup import setup_logging
from app.routes import activities, chat, static_data, user
from app.security import (
    RequestIdMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.state import rate_limit_store  # noqa: F401, pylint: disable=unused-import

settings = get_settings()
logger = setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description=f"""
## {settings.APP_NAME} — {settings.APP_TAGLINE}

{settings.APP_DESCRIPTION}

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
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(chat.router)
app.include_router(activities.router)
app.include_router(static_data.router)
app.include_router(user.router)


@app.get("/health")
async def health() -> dict:
    """Health check endpoint.

    Returns:
        dict: Health status information.
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "tagline": settings.APP_TAGLINE,
        "version": settings.APP_VERSION,
    }


@app.get("/", response_class=HTMLResponse)
async def serve_frontend() -> HTMLResponse:
    """Serve the CarbonCompass frontend application.

    Returns:
        HTMLResponse: Single Page Application HTML content.
    """
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
