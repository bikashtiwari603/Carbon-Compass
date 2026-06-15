# CarbonCompass System Architecture

This document describes the architectural layout, modules, request flow, state management, security model, and scalability considerations of the modular CarbonCompass application.

## 1. Module Responsibilities

The application follows a clean separation of concerns:

- **`main.py`**: The application entry point. Initializes FastAPI, registers global middleware, and mounts routers.
- **`app/config.py`**: Handles configuration parsing, environment loading via Pydantic `BaseSettings`, and caches settings.
- **`app/constants.py`**: Central storage for all static datasets (roadmap, badges, daily tips) and carbon emission factors.
- **`app/models.py`**: Defines Pydantic schema validation rules for all HTTP requests and API responses.
- **`app/state.py`**: Houses centralized, thread-safe in-memory dictionaries for state tracking and metrics.
- **`app/security.py`**: Provides security headers, input sanitization, rate limit validations, and Starlette middlewares.
- **`app/cache.py`**: Implements an in-memory `SimpleCache` (singleton) with custom TTL support.
- **`app/calculator.py`**: Contains the emission calculations based on IPCC and India grid factors.
- **`app/gamification.py`**: Manages points updates, user progression levels, and badge awards.
- **`app/logging_setup.py`**: Provides structured logging configurations with Cloud Logging support.
- **`app/routes/`**: Handles request-response routing for endpoints:
  - `chat.py`: Conversation handling with Google Gemini.
  - `activities.py`: Logging carbon footprint activities and fetching dashboard metrics.
  - `static_data.py`: Serving static information (tips, badges, roadmap, facts).
  - `user.py`: Profile initialization and operational statistics.

---

## 2. Request Flow

```
[ Client (Frontend UI) ]
         │
         ▼
[ ASGI Server (Uvicorn) ]
         │
         ▼ (Middlewares)
┌───────────────────────────────────────┐
│ 1. RequestSizeLimitMiddleware         │ (Rejects body > 1MB)
│ 2. SecurityHeadersMiddleware          │ (Injects CSP, HSTS, CORS)
│ 3. CORSMiddleware & GZipMiddleware   │
└───────────────────────────────────────┘
         │
         ▼ (Routing)
┌───────────────────────────────────────┐
│ API Routers (/api/v1)                 │
│  - chat, activities, static, user    │
└───────────────────────────────────────┘
         │
         ▼ (Checks & Utilities)
┌───────────────────────────────────────┐
│ Input Sanitization & Session Validation│
│ Rate Limiting Checking                │
└───────────────────────────────────────┘
         │
         ▼ (Processing)
┌───────────────────────────────────────┐
│ Cache Check (cache.py)                │ ──► [ Cache Hit: Return ]
└───────────────────────────────────────┘
         │ (Cache Miss)
         ▼
┌───────────────────────────────────────┐
│ - Business Logic (calculator, gamify) │
│ - AI Assistance (chat via Gemini API) │
└───────────────────────────────────────┘
         │
         ▼
[ In-Memory State Updates (state.py) ]
         │
         ▼
[ Cache Entry Populate (cache.py) ]
         │
         ▼
[ Injects X-Request-ID Response Header ]
         │
         ▼
[ Client (JSON/HTML Response) ]
```

---

## 3. State Management

- **Centralized State**: All mutable states (`sessions`, `user_profiles`, `user_points`, `activity_logs`, `stats`) are isolated in `app/state.py`.
- **Thread-Safety**: Read-write access is protected using a Python `threading.RLock()` to prevent race conditions during concurrent requests in production servers.

---

## 4. Security Design

- **Input Sanitization**: HTML and script injections are stripped via standard regex and normalised using Unicode NFKC normalization in `sanitize_input`.
- **Session Identification Validation**: Strict pattern match checking (`^[a-zA-Z0-9_-]+$`) ensures directory traversal attacks are prevented.
- **Payload Constraints**: `RequestSizeLimitMiddleware` inspects content length headers, failing fast with a `413 Payload Too Large` to prevent denial-of-service (DoS).
- **IP-Based Rate Limiting**: Token-bucket sliding window tracks client IPs per endpoint, returning `429 Too Many Requests` when limits are breached.

---

## 5. Scalability Considerations

- **Stateless Application Layer**: The backend logic is entirely stateless. In-memory data structures can be seamlessly moved to a Redis cache and PostgreSQL database when scaling horizontally.
- **Cache-Aside Pattern**: Reduces computing load on static and heavy analytics endpoints by caching payloads with TTL evictions.
