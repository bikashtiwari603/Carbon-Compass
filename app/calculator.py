"""Carbon emission calculation engine for CarbonCompass.

This module provides utility functions for calculating carbon offsets/emissions
based on activity types, estimating annual footprints based on lifestyle choices,
and retrieving the activity metadata catalog.

Data Sources:
    - IPCC AR6 (Intergovernmental Panel on Climate Change Sixth Assessment Report)
    - India Central Electricity Authority (CEA) Carbon Emission Factors (CEF) 2023
    - Our World in Data (Food & Agriculture statistics)
"""

from fastapi import HTTPException

from app.constants import ACTIVITIES_DATA, EMISSION_FACTORS, INDIA_AVERAGE_ANNUAL_TONNES


def calculate_co2(activity_id: str, quantity: float) -> float:
    """Calculate the CO2 equivalent in kilograms for a given activity and quantity.

    Calculates emissions by multiplying quantity by the activity's emission factor.
    Green actions (offsets) return negative numbers indicating net reduction.

    Args:
        activity_id (str): The unique identifier matching an EMISSION_FACTORS key.
        quantity (float): The magnitude of the activity (e.g. distance, weight).

    Returns:
        float: Calculated CO2 emissions in kg (rounded to 4 decimal places).

    Raises:
        HTTPException: If the activity_id is not recognized in the emissions database.
    """
    if activity_id not in EMISSION_FACTORS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown activity ID: {activity_id}",
        )
    return round(quantity * EMISSION_FACTORS[activity_id], 4)


def get_activities_data() -> dict:
    """Retrieve the full metadata structure containing all trackable activities.

    Returns:
        dict: The raw categories and activity information.
    """
    return ACTIVITIES_DATA


def estimate_annual_footprint(
    diet: str,
    transport: str,
    home_energy: str,
    country: str = "India",
) -> float:
    """Estimate a user's annual carbon footprint in tonnes.

    Applies adjustments to the national average baseline footprint based on
    lifestyle choices (diet, transport mode, and energy usage).

    Args:
        diet (str): Dietary habits (e.g. vegan, vegetarian, meat).
        transport (str): Primary transit method (e.g. metro, car).
        home_energy (str): Primary home power description (e.g. solar, heavy_ac).
        country (str): Country of residence. Defaults to 'India'.

    Returns:
        float: The estimated annual footprint in tonnes of CO2 (rounded to 2 decimals).
    """
    # Baseline benchmark
    base = INDIA_AVERAGE_ANNUAL_TONNES

    # Diet adjustments
    diet_adj = {
        "vegan": -0.30,
        "vegetarian": -0.15,
        "omnivore": 0.0,
        "heavy_meat": 0.20,
        "meat": 0.20,
    }
    diet_key = diet.lower().replace(" ", "_")
    base *= 1.0 + diet_adj.get(diet_key, 0.0)

    # Transport adjustments
    transport_adj = {
        "metro": -0.20,
        "bus": -0.15,
        "car": 0.30,
        "motorcycle": 0.15,
        "cycle": -0.40,
        "walk": -0.40,
    }
    trans_key = transport.lower().replace(" ", "_")
    base *= 1.0 + transport_adj.get(trans_key, 0.0)

    # Home energy adjustments
    energy_adj = {
        "solar": -0.25,
        "normal_grid": 0.0,
        "heavy_ac": 0.15,
        "normal": 0.0,
    }
    energy_key = home_energy.lower().replace(" ", "_")
    base *= 1.0 + energy_adj.get(energy_key, 0.0)

    # Country context can scale baseline if not India (for future extensibility)
    if country.lower() != "india":
        pass

    return round(base, 2)
