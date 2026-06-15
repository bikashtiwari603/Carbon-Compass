"""Pydantic request and response models for CarbonCompass.

This module defines the schemas for requests and responses exchanged by
the CarbonCompass API endpoints.
"""

import re
from typing import List

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """Request schema for the AI chat endpoint.

    Attributes:
        message (str): The conversation input message.
        session_id (str): The unique identifier of the user's session.
        mode (str): The chat assistant interaction mode.
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The chat message text submitted by the user. Must be between 1 and 2000 characters.",
    )
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="The alphanumeric session identifier (letters, digits, underscores, dashes).",
    )
    mode: str = Field(
        default="general",
        description="Optional mode setting to alter the assistant's behavior (e.g. general, quiz, calculator).",
    )

    @field_validator("session_id")
    @classmethod
    def validate_session(cls, val: str) -> str:
        """Validate that session ID contains only alphanumeric characters, dashes, and underscores.

        Args:
            val (str): The session ID input.

        Returns:
            str: The validated session ID.

        Raises:
            ValueError: If the session ID format is invalid.
        """
        if not re.match(r"^[a-zA-Z0-9_-]+$", val):
            raise ValueError("Invalid session ID format.")
        return val


class ActivityRequest(BaseModel):
    """Request schema for logging an activity.

    Attributes:
        session_id (str): Unique identifier of the session logging the activity.
        category (str): The broad category of the activity (e.g. transport).
        activity (str): The specific activity sub-type ID.
        quantity (float): The amount or magnitude of the activity.
        unit (str): The measurement unit for the activity quantity.
    """

    session_id: str = Field(
        ...,
        min_length=1,
        description="The alphanumeric session identifier logging this activity.",
    )
    category: str = Field(
        ...,
        description="The category of the activity (e.g. transport, home, food, shopping, green_actions).",
    )
    activity: str = Field(
        ...,
        description="The specific activity identifier (e.g. metro, electricity, tree_planted).",
    )
    quantity: float = Field(
        ...,
        description="The numeric amount of the activity logged. Must be a positive value.",
    )
    unit: str = Field(
        ...,
        description="The unit of measurement corresponding to the activity type (e.g. km, kWh, kg).",
    )

    @field_validator("session_id")
    @classmethod
    def validate_session(cls, val: str) -> str:
        """Validate session ID format.

        Args:
            val (str): The session ID input.

        Returns:
            str: The validated session ID.

        Raises:
            ValueError: If the session ID format is invalid.
        """
        if not re.match(r"^[a-zA-Z0-9_-]+$", val):
            raise ValueError("Invalid session ID format.")
        return val

    @field_validator("quantity")
    @classmethod
    def validate_quantity_positive(cls, val: float) -> float:
        """Ensure the quantity is strictly positive.

        Args:
            val (float): The quantity input.

        Returns:
            float: The validated quantity.

        Raises:
            ValueError: If the quantity is less than or equal to 0.
        """
        if val <= 0:
            raise ValueError("Quantity must be greater than zero.")
        return val


class ProfileRequest(BaseModel):
    """Request schema for creating or updating a user's baseline profile.

    Attributes:
        session_id (str): The unique session identifier.
        country (str): User's country of residence.
        diet (str): Main dietary pattern (e.g. vegetarian, vegan).
        transport (str): Primary mode of transport.
        home_energy (str): Primary home energy type.
    """

    session_id: str = Field(
        ...,
        min_length=1,
        description="The alphanumeric session identifier.",
    )
    country: str = Field(
        default="India",
        description="The country of residence. Defaults to India.",
    )
    diet: str = Field(
        default="",
        description="Primary dietary choices (e.g. heavy_meat, vegetarian, vegan).",
    )
    transport: str = Field(
        default="",
        description="Primary transport choices (e.g. car, motorcycle, metro, cycle).",
    )
    home_energy: str = Field(
        default="",
        description="Primary home energy details (e.g. normal_grid, heavy_ac, solar).",
    )

    @field_validator("session_id")
    @classmethod
    def validate_session(cls, val: str) -> str:
        """Validate session ID format.

        Args:
            val (str): The session ID input.

        Returns:
            str: The validated session ID.

        Raises:
            ValueError: If the session ID format is invalid.
        """
        if not re.match(r"^[a-zA-Z0-9_-]+$", val):
            raise ValueError("Invalid session ID format.")
        return val


class ChatResponse(BaseModel):
    """Response schema returned by the AI chat endpoint.

    Attributes:
        response (str): The AI conversational reply.
        suggestions (List[str]): List of exactly three follow-up prompts.
        points_earned (int): Gamified green points earned for the turn.
        session_id (str): The session identifier for conversation tracking.
    """

    response: str = Field(
        ...,
        description="AI-generated text response from Google Gemini.",
    )
    suggestions: List[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Exactly three suggested follow-up questions for the conversation flow.",
    )
    points_earned: int = Field(
        ...,
        ge=0,
        description="Green points awarded for interacting or adopting green keywords.",
    )
    session_id: str = Field(
        ...,
        description="The session ID associated with the chat transaction.",
    )


class ActivityLogResponse(BaseModel):
    """Response schema returned after logging an activity.

    Attributes:
        co2_kg (float): Total carbon emissions/offsets calculated (negative for offsets).
        points_earned (int): Green points awarded for this activity logging.
        total_points (int): Cumulative green points for this session.
        message (str): Readable status message confirming the activity action.
        new_badges (List[str]): Any badges unlocked during this activity log.
    """

    co2_kg: float = Field(
        ...,
        description="Carbon dioxide equivalent in kilograms (negative value denotes offsets/green actions).",
    )
    points_earned: int = Field(
        ...,
        ge=0,
        description="Green points earned for logging this specific activity.",
    )
    total_points: int = Field(
        ...,
        ge=0,
        description="Cumulative green points earned in this session so far.",
    )
    message: str = Field(
        ...,
        description="Human-readable confirmation message summarizing the calculation.",
    )
    new_badges: List[str] = Field(
        default_factory=list,
        description="List of badge IDs unlocked as a result of logging this activity.",
    )


class HealthResponse(BaseModel):
    """Response schema for the system health check.

    Attributes:
        status (str): Current status of the service (e.g. ok).
        app (str): Name of the application.
        tagline (str): Application slogan.
        version (str): Application semantic version.
    """

    status: str = Field(
        ...,
        description="The system health status, typically 'ok'.",
    )
    app: str = Field(
        ...,
        description="The application name.",
    )
    tagline: str = Field(
        ...,
        description="The application tagline.",
    )
    version: str = Field(
        ...,
        description="The semantic version string.",
    )


class StatsResponse(BaseModel):
    """Response schema for global application usage statistics.

    Attributes:
        total_sessions (int): Cumulative number of sessions created.
        total_messages (int): Cumulative count of processed chat turns.
        total_activities_logged (int): Total count of logged activities.
        uptime_seconds (float): Server operational uptime in seconds.
        cache_hits (int): Count of cache hits.
    """

    total_sessions: int = Field(
        ...,
        ge=0,
        description="Total unique sessions active since startup.",
    )
    total_messages: int = Field(
        ...,
        ge=0,
        description="Total messages exchanged with the AI assistant.",
    )
    total_activities_logged: int = Field(
        ...,
        ge=0,
        description="Total count of carbon activities logged by all sessions.",
    )
    uptime_seconds: float = Field(
        ...,
        ge=0,
        description="Number of seconds the application server has been running.",
    )
    cache_hits: int = Field(
        ...,
        ge=0,
        description="Total number of read requests served by the cache layer.",
    )


class ProfileResponse(BaseModel):
    """Response schema for the user footprint profile setup.

    Attributes:
        estimated_annual_co2_tonnes (float): Estimated annual carbon footprint in tonnes.
        vs_india_average (str): Footprint comparison against India's average.
        vs_global_average (str): Footprint comparison against global average.
        top_reduction_opportunity (str): Personalized high-impact reduction advice.
    """

    estimated_annual_co2_tonnes: float = Field(
        ...,
        description="Estimated annual footprint in tonnes of carbon dioxide.",
    )
    vs_india_average: str = Field(
        ...,
        description="Relative comparison to the national average of India.",
    )
    vs_global_average: str = Field(
        ...,
        description="Relative comparison to the global average.",
    )
    top_reduction_opportunity: str = Field(
        ...,
        description="The recommended highest-priority lifestyle change to lower footprint.",
    )
