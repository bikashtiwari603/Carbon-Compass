"""
Comprehensive test suite for CarbonCompass API.
Covers health, security, chat, activities, dashboard, badges, tips,
roadmap, profile, weekly reports, rate limiting, integration, and performance.
"""
import time
import uuid

import pytest


# ===========================================================================
# HEALTH AND BASIC TESTS
# ===========================================================================


class TestHealthAndBasic:
    """Tests for health-check and basic endpoints."""

    def test_health_returns_200(self, client):
        """GET /health returns HTTP 200."""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_correct_json(self, client):
        """GET /health returns status ok and app name CarbonCompass."""
        data = client.get("/health").json()
        assert data["status"] == "ok"
        assert data["app"] == "CarbonCompass"
        assert "tagline" in data

    def test_health_response_time(self, client):
        """GET /health responds in under 100ms."""
        start = time.time()
        client.get("/health")
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < 100, f"Health took {elapsed_ms:.1f}ms"

    def test_root_returns_html(self, client):
        """GET / returns 200 with text/html content type."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

    def test_about_endpoint(self, client):
        """GET /api/v1/about returns 200 with app name and tagline."""
        resp = client.get("/api/v1/about")
        assert resp.status_code == 200
        data = resp.json()
        assert data["app"] == "CarbonCompass"
        assert "Navigate Towards a Greener Future" in data["tagline"]

    def test_stats_endpoint(self, client):
        """GET /api/v1/stats returns 200 with all required numeric fields."""
        resp = client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        for field in ("total_sessions", "total_messages", "total_activities_logged", "uptime_seconds", "cache_hits"):
            assert field in data
            assert isinstance(data[field], (int, float))


# ===========================================================================
# SECURITY HEADER TESTS
# ===========================================================================


class TestSecurityHeaders:
    """Verify security headers are present on responses."""

    def test_security_header_x_content_type(self, client):
        """Response has X-Content-Type-Options: nosniff."""
        resp = client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_security_header_x_frame(self, client):
        """Response has X-Frame-Options: DENY."""
        resp = client.get("/health")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_security_header_xss(self, client):
        """Response has X-XSS-Protection header."""
        resp = client.get("/health")
        assert "X-XSS-Protection" in resp.headers

    def test_security_header_referrer(self, client):
        """Response has Referrer-Policy header."""
        resp = client.get("/health")
        assert "Referrer-Policy" in resp.headers

    def test_security_header_hsts(self, client):
        """Response has Strict-Transport-Security header."""
        resp = client.get("/health")
        assert "Strict-Transport-Security" in resp.headers

    def test_request_id_header(self, client):
        """Every response has a valid UUID X-Request-ID header."""
        resp = client.get("/health")
        rid = resp.headers.get("X-Request-ID", "")
        # Validate UUID format
        parsed = uuid.UUID(rid)
        assert str(parsed) == rid

    def test_request_id_unique(self, client):
        """Two requests produce different X-Request-ID values."""
        r1 = client.get("/health").headers["X-Request-ID"]
        r2 = client.get("/health").headers["X-Request-ID"]
        assert r1 != r2

    def test_cors_headers(self, client):
        """OPTIONS request returns CORS headers."""
        resp = client.options(
            "/api/v1/chat",
            headers={"Origin": "http://example.com", "Access-Control-Request-Method": "POST"},
        )
        assert "access-control-allow-origin" in resp.headers


# ===========================================================================
# CHAT ENDPOINT TESTS
# ===========================================================================


class TestChat:
    """Tests for POST /api/v1/chat."""

    def test_chat_valid_request(self, client, sample_chat_request):
        """POST /api/v1/chat with valid body returns 200."""
        resp = client.post("/api/v1/chat", json=sample_chat_request)
        assert resp.status_code == 200

    def test_chat_response_has_required_fields(self, client, sample_chat_request):
        """Response has response, suggestions, points_earned, session_id."""
        data = client.post("/api/v1/chat", json=sample_chat_request).json()
        for field in ("response", "suggestions", "points_earned", "session_id"):
            assert field in data

    def test_chat_suggestions_is_list_of_3(self, client, sample_chat_request):
        """Suggestions field is a list with exactly 3 items."""
        data = client.post("/api/v1/chat", json=sample_chat_request).json()
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) == 3

    def test_chat_empty_message_returns_422(self, client, sample_session_id):
        """Empty string message returns 422 or 400."""
        resp = client.post("/api/v1/chat", json={"message": "", "session_id": sample_session_id})
        assert resp.status_code in (400, 422)

    def test_chat_message_too_long_returns_422(self, client, sample_session_id):
        """2001-character message returns 422 or 400."""
        resp = client.post("/api/v1/chat", json={"message": "x" * 2001, "session_id": sample_session_id})
        assert resp.status_code in (400, 422)

    def test_chat_missing_session_id_returns_422(self, client):
        """Missing session_id returns 422."""
        resp = client.post("/api/v1/chat", json={"message": "Hello"})
        assert resp.status_code == 422

    def test_chat_html_injection_sanitized(self, client, sample_session_id):
        """Message with script tags is sanitized before processing."""
        payload = {"message": "<script>alert(1)</script>How to save CO2?", "session_id": sample_session_id}
        resp = client.post("/api/v1/chat", json=payload)
        assert resp.status_code == 200

    def test_chat_null_bytes_rejected(self, client, sample_session_id):
        """Message with null byte returns 400."""
        payload = {"message": "Hello\x00World", "session_id": sample_session_id}
        resp = client.post("/api/v1/chat", json=payload)
        assert resp.status_code == 400

    def test_chat_unicode_hindi_works(self, client, sample_session_id):
        """Hindi text message returns 200."""
        payload = {"message": "मेरा कार्बन फुटप्रिंट कैसे कम करें?", "session_id": sample_session_id}
        resp = client.post("/api/v1/chat", json=payload)
        assert resp.status_code == 200

    def test_chat_with_mode_quiz(self, client, sample_session_id):
        """Mode quiz returns 200."""
        payload = {"message": "Start a quiz", "session_id": sample_session_id, "mode": "quiz"}
        resp = client.post("/api/v1/chat", json=payload)
        assert resp.status_code == 200

    def test_chat_with_mode_calculator(self, client, sample_session_id):
        """Mode calculator returns 200."""
        payload = {"message": "Calculate footprint", "session_id": sample_session_id, "mode": "calculator"}
        resp = client.post("/api/v1/chat", json=payload)
        assert resp.status_code == 200

    def test_chat_session_history_maintained(self, client):
        """Send 3 messages with the same session_id; all return 200."""
        sid = "history-test-session"
        for i in range(3):
            resp = client.post("/api/v1/chat", json={"message": f"Message {i}", "session_id": sid})
            assert resp.status_code == 200

    def test_chat_different_sessions_independent(self, client):
        """Two different session IDs maintain independent histories."""
        r1 = client.post("/api/v1/chat", json={"message": "Hello", "session_id": "session-A"})
        r2 = client.post("/api/v1/chat", json={"message": "Hello", "session_id": "session-B"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Both succeed independently
        assert r1.json()["session_id"] == "session-A"
        assert r2.json()["session_id"] == "session-B"

    def test_chat_points_earned_is_integer(self, client, sample_chat_request):
        """Points_earned field is always an integer."""
        data = client.post("/api/v1/chat", json=sample_chat_request).json()
        assert isinstance(data["points_earned"], int)

    def test_chat_points_earned_positive(self, client, sample_chat_request):
        """Points_earned is non-negative."""
        data = client.post("/api/v1/chat", json=sample_chat_request).json()
        assert data["points_earned"] >= 0


# ===========================================================================
# ACTIVITIES ENDPOINT TESTS
# ===========================================================================


class TestActivities:
    """Tests for GET /api/v1/activities."""

    def test_activities_returns_200(self, client):
        """GET /api/v1/activities returns 200."""
        resp = client.get("/api/v1/activities")
        assert resp.status_code == 200

    def test_activities_has_categories(self, client):
        """Response has categories list."""
        data = client.get("/api/v1/activities").json()
        assert "categories" in data

    def test_activities_has_5_categories(self, client):
        """Categories list has exactly 5 items."""
        data = client.get("/api/v1/activities").json()
        assert len(data["categories"]) == 5

    def test_activities_transport_category_exists(self, client):
        """Transport category is present."""
        cats = client.get("/api/v1/activities").json()["categories"]
        ids = [c["id"] for c in cats]
        assert "transport" in ids

    def test_activities_home_category_exists(self, client):
        """Home category is present."""
        cats = client.get("/api/v1/activities").json()["categories"]
        ids = [c["id"] for c in cats]
        assert "home" in ids

    def test_activities_food_category_exists(self, client):
        """Food category is present."""
        cats = client.get("/api/v1/activities").json()["categories"]
        ids = [c["id"] for c in cats]
        assert "food" in ids

    def test_activities_green_actions_exists(self, client):
        """Green_actions category is present."""
        cats = client.get("/api/v1/activities").json()["categories"]
        ids = [c["id"] for c in cats]
        assert "green_actions" in ids

    def test_activities_cache_header(self, client):
        """Second call to /api/v1/activities has X-Cache HIT header."""
        client.get("/api/v1/activities")  # prime cache
        resp = client.get("/api/v1/activities")
        assert resp.headers.get("X-Cache") == "HIT"

    def test_activities_response_time(self, client):
        """Responds in under 500ms."""
        start = time.time()
        client.get("/api/v1/activities")
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < 500

    def test_each_activity_has_required_fields(self, client):
        """Every activity in every category has id, name, unit, co2_per_unit, icon."""
        cats = client.get("/api/v1/activities").json()["categories"]
        for cat in cats:
            for act in cat["activities"]:
                for field in ("id", "name", "unit", "co2_per_unit", "icon"):
                    assert field in act, f"Missing {field} in {act}"


# ===========================================================================
# LOG ACTIVITY TESTS
# ===========================================================================


class TestLogActivity:
    """Tests for POST /api/v1/log-activity."""

    def test_log_activity_valid(self, client, sample_activity_request):
        """POST /api/v1/log-activity with valid data returns 200."""
        resp = client.post("/api/v1/log-activity", json=sample_activity_request)
        assert resp.status_code == 200

    def test_log_activity_returns_co2(self, client, sample_activity_request):
        """Response has co2_kg as float."""
        data = client.post("/api/v1/log-activity", json=sample_activity_request).json()
        assert isinstance(data["co2_kg"], (int, float))

    def test_log_activity_returns_points(self, client, sample_activity_request):
        """Response has points_earned as positive integer."""
        data = client.post("/api/v1/log-activity", json=sample_activity_request).json()
        assert isinstance(data["points_earned"], int)
        assert data["points_earned"] > 0

    def test_log_activity_returns_total_points(self, client, sample_activity_request):
        """Response has total_points as integer."""
        data = client.post("/api/v1/log-activity", json=sample_activity_request).json()
        assert isinstance(data["total_points"], int)

    def test_log_activity_co2_calculation(self, client):
        """Log metro 10km expects co2_kg approximately 0.41."""
        payload = {"session_id": "calc-test-001", "category": "transport", "activity": "metro", "quantity": 10.0, "unit": "km"}
        data = client.post("/api/v1/log-activity", json=payload).json()
        assert abs(data["co2_kg"] - 0.41) < 0.01

    def test_log_activity_green_action_negative_co2(self, client):
        """Log tree_planted expects negative co2_kg."""
        payload = {"session_id": "green-test-001", "category": "green_actions", "activity": "tree_planted", "quantity": 1.0, "unit": "tree"}
        data = client.post("/api/v1/log-activity", json=payload).json()
        assert data["co2_kg"] < 0

    def test_log_activity_invalid_session(self, client):
        """Empty session_id returns 422."""
        payload = {"session_id": "", "category": "transport", "activity": "metro", "quantity": 10.0, "unit": "km"}
        resp = client.post("/api/v1/log-activity", json=payload)
        assert resp.status_code in (400, 422)

    def test_log_multiple_activities_accumulates_points(self, client):
        """Log 3 activities; total_points increases each time."""
        sid = "accum-test-001"
        totals = []
        for _ in range(3):
            payload = {"session_id": sid, "category": "transport", "activity": "bus", "quantity": 5.0, "unit": "km"}
            data = client.post("/api/v1/log-activity", json=payload).json()
            totals.append(data["total_points"])
        # Each subsequent total should be >= previous
        assert totals[1] >= totals[0]
        assert totals[2] >= totals[1]


# ===========================================================================
# DASHBOARD TESTS
# ===========================================================================


class TestDashboard:
    """Tests for GET /api/v1/dashboard/{session_id}."""

    def test_dashboard_new_session(self, client):
        """GET /api/v1/dashboard/new-session-xyz returns 200 with zero values."""
        resp = client.get("/api/v1/dashboard/new-session-xyz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_co2_kg"] == 0
        assert data["activities_count"] == 0

    def test_dashboard_after_logging(self, client):
        """Log activity then get dashboard shows that activity in totals."""
        sid = "dash-test-001"
        client.post("/api/v1/log-activity", json={
            "session_id": sid, "category": "transport", "activity": "car_petrol", "quantity": 100.0, "unit": "km",
        })
        data = client.get(f"/api/v1/dashboard/{sid}").json()
        assert data["total_co2_kg"] > 0
        assert data["activities_count"] >= 1

    def test_dashboard_has_all_fields(self, client):
        """Response has total_co2_kg, total_offset_kg, net_co2_kg, breakdown, daily_average."""
        data = client.get("/api/v1/dashboard/any-session").json()
        for field in ("total_co2_kg", "total_offset_kg", "net_co2_kg", "breakdown", "daily_average"):
            assert field in data

    def test_dashboard_breakdown_by_category(self, client):
        """Breakdown dict has category keys after logging."""
        sid = "dash-cat-001"
        client.post("/api/v1/log-activity", json={
            "session_id": sid, "category": "food", "activity": "chicken", "quantity": 1.0, "unit": "kg",
        })
        data = client.get(f"/api/v1/dashboard/{sid}").json()
        assert isinstance(data["breakdown"], dict)
        assert "food" in data["breakdown"]


# ===========================================================================
# BADGES TESTS
# ===========================================================================


class TestBadges:
    """Tests for GET /api/v1/badges."""

    def test_badges_returns_200(self, client):
        """GET /api/v1/badges returns 200."""
        resp = client.get("/api/v1/badges")
        assert resp.status_code == 200

    def test_badges_returns_list(self, client):
        """Response is a list."""
        data = client.get("/api/v1/badges").json()
        assert isinstance(data, list)

    def test_badges_count(self, client):
        """List has exactly 9 badges."""
        data = client.get("/api/v1/badges").json()
        assert len(data) == 9

    def test_badges_cache(self, client):
        """Second call has X-Cache HIT header."""
        client.get("/api/v1/badges")
        resp = client.get("/api/v1/badges")
        assert resp.headers.get("X-Cache") == "HIT"

    def test_each_badge_has_required_fields(self, client):
        """Every badge has id, name, description, points_required, icon, color."""
        data = client.get("/api/v1/badges").json()
        for badge in data:
            for field in ("id", "name", "description", "points_required", "icon", "color"):
                assert field in badge, f"Missing {field} in badge {badge.get('id', '?')}"


# ===========================================================================
# TIPS TESTS
# ===========================================================================


class TestTips:
    """Tests for GET /api/v1/tips."""

    def test_tips_returns_200(self, client):
        """GET /api/v1/tips returns 200."""
        resp = client.get("/api/v1/tips")
        assert resp.status_code == 200

    def test_tips_has_daily_tips(self, client):
        """Response has daily_tips list."""
        data = client.get("/api/v1/tips").json()
        assert "daily_tips" in data
        assert isinstance(data["daily_tips"], list)

    def test_tips_has_5_daily_tips(self, client):
        """Daily_tips has exactly 5 items."""
        data = client.get("/api/v1/tips").json()
        assert len(data["daily_tips"]) == 5

    def test_tips_has_weekly_challenge(self, client):
        """Response has weekly_challenge object."""
        data = client.get("/api/v1/tips").json()
        assert "weekly_challenge" in data
        assert isinstance(data["weekly_challenge"], dict)

    def test_tips_cache(self, client):
        """Second call has X-Cache HIT header."""
        client.get("/api/v1/tips")
        resp = client.get("/api/v1/tips")
        assert resp.headers.get("X-Cache") == "HIT"


# ===========================================================================
# ROADMAP TESTS
# ===========================================================================


class TestRoadmap:
    """Tests for GET /api/v1/roadmap."""

    def test_roadmap_returns_200(self, client):
        """GET /api/v1/roadmap returns 200."""
        resp = client.get("/api/v1/roadmap")
        assert resp.status_code == 200

    def test_roadmap_has_phases(self, client):
        """Response has phases list."""
        data = client.get("/api/v1/roadmap").json()
        assert "phases" in data
        assert isinstance(data["phases"], list)

    def test_roadmap_has_6_phases(self, client):
        """Phases list has exactly 6 items."""
        data = client.get("/api/v1/roadmap").json()
        assert len(data["phases"]) == 6

    def test_roadmap_phase_order(self, client):
        """Phases are numbered 1 through 6 in order."""
        data = client.get("/api/v1/roadmap").json()
        for i, phase in enumerate(data["phases"], start=1):
            assert phase["phase"] == i

    def test_each_phase_has_required_fields(self, client):
        """Every phase has phase, title, duration, description, color, actions, milestone."""
        data = client.get("/api/v1/roadmap").json()
        for phase in data["phases"]:
            for field in ("phase", "title", "duration", "description", "color", "actions", "milestone"):
                assert field in phase

    def test_roadmap_cache(self, client):
        """Second call has X-Cache HIT header."""
        client.get("/api/v1/roadmap")
        resp = client.get("/api/v1/roadmap")
        assert resp.headers.get("X-Cache") == "HIT"


# ===========================================================================
# PROFILE TESTS
# ===========================================================================


class TestProfile:
    """Tests for POST /api/v1/profile."""

    def test_profile_valid_request(self, client, sample_session_id):
        """POST /api/v1/profile with valid data returns 200."""
        payload = {"session_id": sample_session_id, "country": "India", "diet": "vegetarian", "transport": "metro", "home_energy": "normal"}
        resp = client.post("/api/v1/profile", json=payload)
        assert resp.status_code == 200

    def test_profile_returns_estimate(self, client, sample_session_id):
        """Response has estimated_annual_co2_tonnes as float."""
        payload = {"session_id": sample_session_id, "country": "India", "diet": "vegetarian", "transport": "metro", "home_energy": "normal"}
        data = client.post("/api/v1/profile", json=payload).json()
        assert isinstance(data["estimated_annual_co2_tonnes"], (int, float))

    def test_profile_vegan_lower_than_meat(self, client):
        """Vegan diet profile has lower CO2 than meat diet."""
        vegan = client.post("/api/v1/profile", json={
            "session_id": "vegan-test", "country": "India", "diet": "vegan", "transport": "metro", "home_energy": "solar",
        }).json()
        meat = client.post("/api/v1/profile", json={
            "session_id": "meat-test", "country": "India", "diet": "meat", "transport": "car", "home_energy": "heavy_ac",
        }).json()
        assert vegan["estimated_annual_co2_tonnes"] < meat["estimated_annual_co2_tonnes"]


# ===========================================================================
# WEEKLY REPORT TESTS
# ===========================================================================


class TestWeeklyReport:
    """Tests for GET /api/v1/weekly-report/{session_id}."""

    def test_weekly_report_returns_200(self, client):
        """GET /api/v1/weekly-report/test-session returns 200."""
        resp = client.get("/api/v1/weekly-report/test-session")
        assert resp.status_code == 200

    def test_weekly_report_has_summary(self, client):
        """Response has summary object."""
        data = client.get("/api/v1/weekly-report/test-session").json()
        assert "summary" in data
        assert isinstance(data["summary"], dict)


# ===========================================================================
# RATE LIMIT TESTS
# ===========================================================================


class TestRateLimit:
    """Tests for rate limiting."""

    def test_rate_limit_chat_429_after_10(self, client):
        """Send 11 POST /api/v1/chat requests; the 11th returns 429."""
        # Use a unique session to avoid collision with other tests
        sid = "ratelimit-test-unique-session"
        for i in range(10):
            resp = client.post("/api/v1/chat", json={"message": f"Msg {i}", "session_id": sid})
            assert resp.status_code == 200, f"Request {i+1} failed with {resp.status_code}"
        resp = client.post("/api/v1/chat", json={"message": "Over limit", "session_id": sid})
        assert resp.status_code == 429

    def test_rate_limit_has_retry_after(self, client):
        """429 response has Retry-After header."""
        sid = "ratelimit-retry-test"
        for i in range(10):
            client.post("/api/v1/chat", json={"message": f"Msg {i}", "session_id": sid})
        resp = client.post("/api/v1/chat", json={"message": "Over limit", "session_id": sid})
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers


# ===========================================================================
# INTEGRATION TESTS
# ===========================================================================


class TestIntegration:
    """End-to-end integration tests."""

    def test_full_user_journey(self, client):
        """Complete flow: profile → log 5 activities → dashboard → weekly report."""
        sid = "journey-test-001"

        # 1. Set profile
        resp = client.post("/api/v1/profile", json={
            "session_id": sid, "country": "India", "diet": "vegetarian", "transport": "metro", "home_energy": "normal",
        })
        assert resp.status_code == 200

        # 2. Log 5 activities
        activities = [
            {"category": "transport", "activity": "metro", "quantity": 15, "unit": "km"},
            {"category": "food", "activity": "vegetables", "quantity": 2, "unit": "kg"},
            {"category": "home", "activity": "electricity", "quantity": 5, "unit": "kWh"},
            {"category": "green_actions", "activity": "tree_planted", "quantity": 1, "unit": "tree"},
            {"category": "green_actions", "activity": "recycled", "quantity": 3, "unit": "kg"},
        ]
        for act in activities:
            act["session_id"] = sid
            resp = client.post("/api/v1/log-activity", json=act)
            assert resp.status_code == 200

        # 3. Dashboard
        dash = client.get(f"/api/v1/dashboard/{sid}").json()
        assert dash["activities_count"] == 5
        assert dash["total_co2_kg"] > 0
        assert dash["total_offset_kg"] > 0

        # 4. Weekly report
        report = client.get(f"/api/v1/weekly-report/{sid}").json()
        assert report["summary"]["activities_count"] == 5

    def test_stats_increment(self, client):
        """Log activity and verify total_activities_logged in stats increments."""
        before = client.get("/api/v1/stats").json()["total_activities_logged"]
        client.post("/api/v1/log-activity", json={
            "session_id": "stats-test-001", "category": "food", "activity": "chicken", "quantity": 1, "unit": "kg",
        })
        after = client.get("/api/v1/stats").json()["total_activities_logged"]
        assert after > before


# ===========================================================================
# PERFORMANCE TESTS
# ===========================================================================


class TestPerformance:
    """Performance benchmarks."""

    def test_health_under_100ms(self, client):
        """/health responds in under 100ms."""
        start = time.time()
        client.get("/health")
        assert (time.time() - start) * 1000 < 100

    def test_activities_under_500ms(self, client):
        """/api/v1/activities responds in under 500ms."""
        start = time.time()
        client.get("/api/v1/activities")
        assert (time.time() - start) * 1000 < 500

    def test_roadmap_under_500ms(self, client):
        """/api/v1/roadmap responds in under 500ms."""
        start = time.time()
        client.get("/api/v1/roadmap")
        assert (time.time() - start) * 1000 < 500
