"""
Data Models and Processors for Farm Agent

Contains all data models and processor classes for weather, market prices, and sheet data.
"""

import aiohttp
from loguru import logger
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class HourlyWeatherData(BaseModel):
    """Hourly weather forecast data model."""
    time: str
    temperature: float
    condition: str


class WeatherData(BaseModel):
    """Weather information data model."""
    location: str
    date: str
    current_temperature: float
    condition: str
    high_temperature: float
    low_temperature: float
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    sunrise: Optional[str] = None
    sunset: Optional[str] = None
    hourly_forecast: List[HourlyWeatherData]
    temperature_unit: str = "°C"
    wind_unit: str = "km/h"


class MarketPriceData(BaseModel):
    """Market price data model for agricultural commodities."""
    commodity: str
    market: str
    state: str
    price_min: float
    price_max: float
    price_modal: float
    unit: str
    date: str
    arrival: Optional[str] = None