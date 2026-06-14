"""
Shared test fixtures for CarbonCompass test suite.
"""
import os
import sys
from unittest.mock import MagicMock, patch

# Set environment variable BEFORE importing app
os.environ["GEMINI_API_KEY"] = "test_fake_key_for_testing_only_1234567890"

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport


# Mock Gemini before importing the app module
_mock_response = MagicMock()
_mock_response.text = "This is a test response about carbon footprint reduction. 🌱"

_mock_model_instance = MagicMock()
_mock_model_instance.generate_content.return_value = _mock_response

_patcher = patch("google.generativeai.GenerativeModel", return_value=_mock_model_instance)
_patcher.start()

from main import app, rate_limit_store  # noqa: E402


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Clear rate limit store before every test to prevent cross-test pollution."""
    rate_limit_store.clear()
    yield
    rate_limit_store.clear()


@pytest.fixture
def client():
    """Returns a synchronous TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Returns an async HTTPX client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_session_id():
    """Returns a consistent test session ID."""
    return "test-session-abc123"


@pytest.fixture
def sample_chat_request(sample_session_id):
    """Returns a valid chat request payload."""
    return {
        "message": "How do I reduce my carbon footprint?",
        "session_id": sample_session_id,
        "mode": "general",
    }


@pytest.fixture
def sample_activity_request(sample_session_id):
    """Returns a valid activity log request payload."""
    return {
        "session_id": sample_session_id,
        "category": "transport",
        "activity": "metro",
        "quantity": 10.0,
        "unit": "km",
    }
