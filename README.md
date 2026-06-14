# 🌍 CarbonCompass

> **Navigate Towards a Greener Future**

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-AI-orange?logo=google)](https://ai.google.dev)
[![Cloud Run](https://img.shields.io/badge/Google%20Cloud%20Run-Deployed-4285F4?logo=googlecloud)](https://cloud.google.com/run)
[![Tests](https://img.shields.io/badge/Tests-79%20Passing-brightgreen?logo=pytest)](https://github.com/bikashtiwari603/Carbon-Compass)
[![License](https://img.shields.io/badge/License-Non--Commercial-lightgrey)](LICENSE)

AI-powered carbon footprint tracking web application built with FastAPI, Google Gemini AI, and a premium dark-theme single-page frontend. Designed for the Indian market with global applicability.

**Topics:** `python` `fastapi` `google-gemini` `carbon-footprint` `climate-action` `google-cloud-run` `sustainability` `india` `ai-powered` `gamification`

---

## 🌐 Live Demo

> ### **[https://carboncompass-rlzbi2esba-uc.a.run.app/](https://carboncompass-rlzbi2esba-uc.a.run.app/)**

🚀 Fully deployed on Google Cloud Run · No sign-up required · Works on mobile

---

## 📸 Screenshots

> | Home Dashboard | Activity Tracker | Carbon Quiz | Badges System |
> |---|---|---|---|
> | Hero stats, rotating facts, feature cards with glassmorphism | 5 categories, 20+ activities, live CO₂ meter | 30 expert questions with timer and scoring | 9 earnable badges with progress tracking |

The interface features:
- 🌙 **Dark / Light mode** with smooth circular reveal transition
- 🍃 **Leaf particle cursor** — leaves trail your mouse movements
- 🏕️ **Forest-themed winding roadmap** with animated path and floating leaf
- 🔮 **Glassmorphism 3D cards** that tilt on hover with neon glow effects

---

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Google Services](#google-services)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Development Journey](#development-journey)
- [Deployment to Google Cloud Run](#deployment-to-google-cloud-run)
- [Accessibility](#accessibility)
- [Security](#security)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **AI Carbon Assistant** | Google Gemini 1.5 Flash powered chat with carbon expertise |
| 📊 **Live Dashboard** | Real-time CO₂ breakdown, trend charts, comparison gauges |
| 📝 **Activity Tracker** | 20+ trackable activities across 5 categories |
| 🗺️ **Reduction Roadmap** | 6-phase journey from awareness to net-zero |
| 🧠 **Carbon Quiz** | 30 expert questions with instant scoring |
| 💡 **Daily Tips** | Personalized eco-actions with one-tap logging |
| 🏆 **Gamification** | 9 badges, points system, level progression, leaderboard |
| 📈 **Weekly Report** | AI-generated personal carbon report |
| 🇮🇳 **India Focus** | PM Surya Ghar, EV subsidies, metro transport, local context |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Vanilla HTML5 + CSS3 + JavaScript (single `index.html`, all inline) |
| **Backend** | Python 3.12 · FastAPI · Uvicorn |
| **AI** | Google Gemini API (`gemini-1.5-flash`) |
| **Deployment** | Google Cloud Run (via Docker) |
| **Logging** | Google Cloud Logging (falls back to standard logging) |

---

## ☁️ Google Services

1. **Google Gemini AI** — Powers the conversational AI carbon assistant
2. **Google Cloud Run** — Serverless container deployment
3. **Google Cloud Logging** — Structured production logging
4. **Google Analytics 4** — User engagement tracking (via GA4 tag)
5. **Google Secret Manager** — Secure API key storage in production
6. **Google Fonts** — Inter & Poppins typography

---

## 📁 Project Structure

```
Carbon-Compass/
├── main.py              # FastAPI application — all endpoints, middleware, AI
├── requirements.txt     # Python dependencies
├── Dockerfile           # Cloud Run deployment container (non-root user)
├── .dockerignore        # Excludes dev files from Docker image
├── .env.example         # Environment variable template
├── .gitignore           # Ignores secrets, caches, large assets
├── README.md            # This file
├── CONTRIBUTING.md      # Contribution guidelines
├── pytest.ini           # Test configuration
├── conftest.py          # Shared test fixtures & Gemini mock
├── test_main.py         # 79 comprehensive tests
└── static/
    └── index.html       # Complete SPA — all CSS & JS inline
```

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/bikashtiwari603/Carbon-Compass.git
cd Carbon-Compass
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your Gemini API Key

Get a free key at: https://aistudio.google.com/app/apikey

```bash
# Windows PowerShell
$env:GEMINI_API_KEY = "your_actual_api_key_here"

# Linux/macOS
export GEMINI_API_KEY="your_actual_api_key_here"
```

### 4. Run the development server

```bash
uvicorn main:app --reload --port 8080
```

Open: http://localhost:8080

---

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | **Yes** | Google Gemini API key from AI Studio |
| `GOOGLE_CLOUD_PROJECT` | No | GCP Project ID for Cloud Logging |
| `GA4_MEASUREMENT_ID` | No | Google Analytics 4 Measurement ID |
| `PORT` | No | Server port (default: 8080) |

---

## 📡 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serve frontend SPA |
| `GET` | `/health` | Health check (Cloud Run) |
| `GET` | `/api/v1/about` | App metadata + live URL + GitHub |
| `GET` | `/api/v1/stats` | Global usage statistics |

### AI & User Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/chat` | AI chat via Gemini |
| `POST` | `/api/v1/profile` | Set user profile & get baseline |
| `GET` | `/api/v1/dashboard/{session_id}` | Full dashboard data |
| `GET` | `/api/v1/weekly-report/{session_id}` | Weekly CO₂ report |

### Data Endpoints (Cached)

| Method | Endpoint | Cache TTL | Description |
|---|---|---|---|
| `GET` | `/api/v1/activities` | 300s | All 20+ trackable activities |
| `POST` | `/api/v1/log-activity` | — | Log an activity |
| `GET` | `/api/v1/badges` | 300s | All 9 badges |
| `GET` | `/api/v1/tips` | 300s | Daily tips + weekly challenge |
| `GET` | `/api/v1/roadmap` | 300s | 6-phase reduction roadmap |

### Carbon Calculation Values

| Activity | CO₂ Factor |
|---|---|
| Car (petrol) | 0.21 kg/km |
| Metro/Train | 0.041 kg/km |
| Domestic Flight | 0.255 kg/km |
| India Electricity | 0.82 kg/kWh |
| Beef | 27.0 kg/kg |
| Tree planted | −21.0 kg/tree/year |

---

## 🧪 Testing

### Run all tests

```bash
pytest -v
```

### Run specific test groups

```bash
pytest -v -k "TestHealth"         # Health tests
pytest -v -k "TestSecurity"       # Security header tests
pytest -v -k "TestChat"           # AI chat tests
pytest -v -k "TestRateLimit"      # Rate limiting tests
pytest -v -k "TestIntegration"    # Full user journey tests
pytest -v -k "TestPerformance"    # Response time tests
```

### Test Coverage — 79 Tests, All Passing ✅

- ✅ **Health & Basic** — 6 tests
- ✅ **Security Headers** — 8 tests (X-Content-Type, X-Frame-Options, HSTS, UUID request IDs, CORS)
- ✅ **Chat Endpoint** — 15 tests (validation, sanitisation, modes, session history, Unicode)
- ✅ **Activities** — 10 tests (structure, cache, response time, field validation)
- ✅ **Log Activity** — 8 tests (CO₂ calculation, points, green actions, accumulation)
- ✅ **Dashboard** — 4 tests (new session, post-log, all fields, category breakdown)
- ✅ **Badges** — 5 tests (count=9, cache, field validation)
- ✅ **Tips** — 5 tests (daily tips count=5, weekly challenge, cache)
- ✅ **Roadmap** — 6 tests (phase count=6, ordering, field validation, cache)
- ✅ **Profile** — 3 tests (valid request, estimate, vegan < meat)
- ✅ **Weekly Report** — 2 tests
- ✅ **Rate Limiting** — 2 tests (429 after 10 chat requests, Retry-After header)
- ✅ **Integration** — 2 tests (full user journey, stats increment)
- ✅ **Performance** — 3 tests (health <100ms, activities <500ms, roadmap <500ms)

---

## 🗓️ Development Journey

The development of CarbonCompass followed an iterative, test-driven approach:

```
feat: initial project setup and FastAPI backend structure
feat: added Google Gemini AI chat integration with session history
feat: implemented activity tracker with 20+ CO2 calculations
feat: added gamification system with 9 badges and points progression
feat: integrated Google Cloud Logging and Analytics 4
feat: added comprehensive test suite with 79+ automated tests
feat: security hardening — CSP, HSTS, rate limiting, input sanitisation
feat: performance optimisation — in-memory caching, GZip compression
feat: premium UI with glassmorphism cards, forest roadmap, leaf cursor
feat: dark/light theme with circular reveal transition animation
feat: WCAG AA accessibility — full ARIA roles, keyboard navigation
feat: final deployment to Google Cloud Run with Secret Manager
docs: improve README, fix stat animations, add badges and screenshots
```

---

## 🐳 Deployment to Google Cloud Run

### Prerequisites

```bash
# Install Google Cloud SDK
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Store API Key in Secret Manager

```bash
echo -n "your_gemini_api_key" | gcloud secrets create gemini-api-key --data-file=-
```

### Deploy from Source (Recommended)

```bash
gcloud run deploy carboncompass \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10
```

### Required IAM Roles for Compute Service Account

```bash
PROJECT_NUMBER=YOUR_PROJECT_NUMBER
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member=serviceAccount:${SA} --role=roles/storage.objectViewer
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member=serviceAccount:${SA} --role=roles/artifactregistry.writer
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member=serviceAccount:${SA} --role=roles/logging.logWriter
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member=serviceAccount:${SA} --role=roles/secretmanager.secretAccessor
```

### Enable Cloud Logging

Cloud Logging is automatically configured when deployed to Cloud Run with a service account that has the `logging.logEntries.create` permission.

---

## ♿ Accessibility (WCAG AA)

- Skip navigation link
- Full ARIA roles (`role=main`, `role=navigation`, `role=tablist`, `role=tab`, `role=tabpanel`)
- `aria-selected`, `aria-controls`, `aria-labelledby` on all tabs
- `aria-live=polite` on chat messages, dashboard updates
- `aria-live=assertive` on error toasts
- `aria-busy` on loading states
- `aria-expanded` on collapsible elements
- `aria-pressed` on toggle buttons
- `aria-valuenow/min/max` on progress bars and gauges
- `prefers-reduced-motion` respected for all animations
- All interactive elements keyboard navigable
- Focus-visible styling throughout

---

## 🔒 Security

| Feature | Implementation |
|---|---|
| Security headers | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `HSTS`, `Permissions-Policy`, `CSP` |
| Rate limiting | 10 req/min for chat, 60 req/min for other endpoints (per IP, in-memory) |
| Input sanitisation | HTML strip, script removal, null byte rejection, repeated char detection, Unicode normalisation |
| Session ID validation | Regex `[a-zA-Z0-9_-]+` only |
| Request tracing | UUID `X-Request-ID` on every response |
| API key validation | Startup check for placeholder/short keys |
| Secret management | Gemini API key stored in GCP Secret Manager — never in code |
| Container security | Runs as non-root `appuser` inside Docker |
| CORS | Configured via `CORSMiddleware` |

---

## 📊 Carbon Data Sources

- IPCC Sixth Assessment Report (AR6)
- India Greenhouse Gas Inventory (MoEFCC)
- Our World in Data — CO₂ emissions
- IEA — India Electricity Grid Emission Factor (0.82 kg CO₂/kWh)
- EPA — GHG Emission Factors Hub

---

## 🌱 About the Mission

> *"Most individuals have no idea what their carbon footprint is or how their daily choices contribute to climate change. CarbonCompass bridges this awareness gap with simple tracking, personalized AI guidance, and actionable reduction roadmaps."*

**Average Indian CO₂:** 1.9 tonnes/year  
**Global Average:** 4.8 tonnes/year  
**Paris Agreement Target:** <2 tonnes/person/year  
**India Net Zero Commitment:** 2070  

---

## 🤝 Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

Non-commercial. Built for educational and awareness purposes.

---

*Built with 💚 for a greener future · Powered by Google Gemini AI · Deployed on Google Cloud Run*
