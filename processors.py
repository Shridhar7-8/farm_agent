import aiohttp
import random
from datetime import datetime
from typing import Optional, Dict, Any
from config import config
from models import WeatherData, MarketPriceData, HourlyWeatherData
from utils import logger

class SharedAsyncClient:
    """Singleton for aiohttp sessions (orthogonality, reuse)."""
    _session = None

    @classmethod
    async def get_session(cls):
        if cls._session is None or cls._session.closed:
            cls._session = aiohttp.ClientSession(headers={'User-Agent': 'AI-Farm-Management-Assistant/1.0'})
        return cls._session

class MarketPriceProcessor:
    """Market price processor using Agmarknet/data.gov.in for Indian mandi prices."""
    
    def __init__(self):
        self.cache: Dict[str, tuple[MarketPriceData, datetime]] = {}
        self.cache_duration = config.cache_duration_market
        
        self.commodity_mapping = {
            'rice': 'Rice',
            'paddy': 'Paddy(Dhan)(Common)',
            'wheat': 'Wheat',
            'corn': 'Maize',
            'maize': 'Maize',
            'cotton': 'Cotton',
            'soybean': 'Soyabean',
            'soya': 'Soyabean',
            'groundnut': 'Groundnut',
            'peanut': 'Groundnut',
            'mustard': 'Mustard',
            'rapeseed': 'Rapeseed',
            'chickpea': 'Gram(Whole)',
            'chana': 'Gram(Whole)',
            'gram': 'Gram(Whole)',
            'tur': 'Arhar (Tur/Red Gram)(Whole)',
            'arhar': 'Arhar (Tur/Red Gram)(Whole)',
            'pigeon pea': 'Arhar (Tur/Red Gram)(Whole)',
            'moong': 'Moong(Green Gram)',
            'green gram': 'Moong(Green Gram)',
            'urad': 'Black Gram',
            'black gram': 'Black Gram',
            'sugarcane': 'Sugarcane',
            'potato': 'Potato',
            'onion': 'Onion',
            'tomato': 'Tomato',
            'bajra': 'Bajra(Pearl Millet/Cumbu)',
            'pearl millet': 'Bajra(Pearl Millet/Cumbu)',
            'jowar': 'Jowar(Sorghum)',
            'sorghum': 'Jowar(Sorghum)',
        }
        
        self.sample_data = {
            'Rice': {'markets': ['Delhi', 'Mumbai', 'Bangalore', 'Chennai'], 'price_range': (2000, 3500)},
            'Wheat': {'markets': ['Delhi', 'Punjab', 'Haryana', 'UP'], 'price_range': (2200, 2800)},
            'Paddy(Dhan)(Common)': {'markets': ['Punjab', 'Haryana', 'UP', 'West Bengal'], 'price_range': (1800, 2400)},
            'Maize': {'markets': ['Karnataka', 'Maharashtra', 'Bihar', 'UP'], 'price_range': (1600, 2200)},
            'Cotton': {'markets': ['Gujarat', 'Maharashtra', 'Telangana', 'Punjab'], 'price_range': (5500, 7500)},
            'Soyabean': {'markets': ['Madhya Pradesh', 'Maharashtra', 'Rajasthan'], 'price_range': (3800, 4500)},
            'Groundnut': {'markets': ['Gujarat', 'Rajasthan', 'Tamil Nadu'], 'price_range': (5000, 6500)},
            'Gram(Whole)': {'markets': ['Madhya Pradesh', 'Maharashtra', 'Rajasthan'], 'price_range': (4500, 5500)},
            'Arhar (Tur/Red Gram)(Whole)': {'markets': ['Maharashtra', 'Karnataka', 'Madhya Pradesh'], 'price_range': (6000, 7500)},
            'Moong(Green Gram)': {'markets': ['Rajasthan', 'Maharashtra', 'Karnataka'], 'price_range': (6500, 8000)},
            'Sugarcane': {'markets': ['Uttar Pradesh', 'Maharashtra', 'Karnataka'], 'price_range': (280, 350)},
            'Potato': {'markets': ['Uttar Pradesh', 'West Bengal', 'Bihar'], 'price_range': (800, 1500)},
            'Onion': {'markets': ['Maharashtra', 'Karnataka', 'Gujarat'], 'price_range': (1200, 2500)},
            'Tomato': {'markets': ['Karnataka', 'Andhra Pradesh', 'Maharashtra'], 'price_range': (1000, 2000)},
        }

    async def get_market_price(self, crop_name: str) -> Optional[MarketPriceData]:
        """Get market price for a given crop from Indian mandis."""
        try:
            crop_key = crop_name.lower().strip()
            cache_key = crop_key
            current_time = datetime.now()
            
            if cache_key in self.cache:
                cached_data, cache_time = self.cache[cache_key]
                if (current_time - cache_time).seconds < self.cache_duration:
                    logger.debug(f"Using cached market price data for {crop_name}")
                    return cached_data

            commodity = self.commodity_mapping.get(crop_key)
            
            if not commodity:
                logger.warning(f"Commodity {crop_name} not found in mapping")
                return None
            
            if commodity not in self.sample_data:
                logger.warning(f"No market data available for {commodity}")
                return None
            
            data = self.sample_data[commodity]
            markets = data['markets']
            price_range = data['price_range']
            
            price_min = price_range[0]
            price_max = price_range[1]
            price_modal = int((price_min + price_max) / 2)
            
            price_min = int(price_min + random.randint(-100, 50))
            price_max = int(price_max + random.randint(-50, 100))
            
            market = random.choice(markets)
            
            state_mapping = {
                'Delhi': 'Delhi',
                'Mumbai': 'Maharashtra',
                'Bangalore': 'Karnataka',
                'Chennai': 'Tamil Nadu',
                'Punjab': 'Punjab',
                'Haryana': 'Haryana',
                'UP': 'Uttar Pradesh',
                'West Bengal': 'West Bengal',
                'Karnataka': 'Karnataka',
                'Maharashtra': 'Maharashtra',
                'Bihar': 'Bihar',
                'Gujarat': 'Gujarat',
                'Telangana': 'Telangana',
                'Madhya Pradesh': 'Madhya Pradesh',
                'Rajasthan': 'Rajasthan',
                'Tamil Nadu': 'Tamil Nadu',
                'Andhra Pradesh': 'Andhra Pradesh',
                'Uttar Pradesh': 'Uttar Pradesh',
            }
            
            state = state_mapping.get(market, market)
            
            price_data = MarketPriceData(
                commodity=commodity,
                market=f"{market} Mandi",
                state=state,
                price_min=price_min,
                price_max=price_max,
                price_modal=price_modal,
                unit="₹/Quintal",
                date=datetime.now().strftime('%d-%b-%Y'),
                arrival="Good" if random.random() > 0.5 else "Moderate"
            )
            
            self.cache[cache_key] = (price_data, current_time)
            
            logger.info(f"Fetched market price for {commodity}: ₹{price_modal}/quintal at {market}")
            return price_data

        except Exception as e:
            logger.error(f"Market price error for {crop_name}: {e}")
            return None

class WeatherDataProcessor:
    """Weather data processor using Open-Meteo API for real-time weather information."""
    
    def __init__(self):
        self.cache: Dict[str, tuple[WeatherData, datetime]] = {}
        self.geocoding_cache: Dict[str, tuple] = {}
        self.cache_duration = config.cache_duration_weather

    async def get_coordinates(self, location: str) -> Optional[tuple]:
        """Get latitude and longitude for a given location using geocoding."""
        try:
            if location.lower() in self.geocoding_cache:
                return self.geocoding_cache[location.lower()]
            
            common_cities = {
                'delhi': (28.7041, 77.1025),
                'mumbai': (19.0760, 72.8777),
                'bangalore': (12.9716, 77.5946),
                'bengaluru': (12.9716, 77.5946),
                'chennai': (13.0827, 80.2707),
                'kolkata': (22.5726, 88.3639),
                'hyderabad': (17.3850, 78.4867),
                'pune': (18.5204, 73.8567),
                'ahmedabad': (23.0225, 72.5714),
                'jaipur': (26.9124, 75.7873),
                'punjab': (30.9010, 75.8573),
            }
            
            location_key = location.lower().strip()
            if location_key in common_cities:
                coords = common_cities[location_key]
                self.geocoding_cache[location_key] = coords
                logger.info(f"Found coordinates for {location}: {coords}")
                return coords
            
            session = await SharedAsyncClient.get_session()
            headers = {'User-Agent': 'AI-Farm-Management-Assistant/1.0'}
            url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json&limit=1"
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        lat = float(data[0]['lat'])
                        lon = float(data[0]['lon'])
                        coords = (lat, lon)
                        self.geocoding_cache[location_key] = coords
                        logger.info(f"Geocoded {location} to: {coords}")
                        return coords
            
            logger.error(f"Could not geocode location: {location}")
            return None
            
        except Exception as e:
            logger.error(f"Error geocoding location {location}: {e}")
            return None

    def get_weather_condition(self, weather_code: int) -> str:
        """Convert weather code to human-readable condition."""
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 
            3: "Overcast", 45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        return weather_codes.get(weather_code, "Unknown")

    async def get_weather_data(self, location: str) -> Optional[WeatherData]:
        """Get weather data for a given location."""
        try:
            logger.info(f"Fetching weather data for location: {location}")
            cache_key = location.lower()
            current_time = datetime.now()
            
            if cache_key in self.cache:
                cached_data, cache_time = self.cache[cache_key]
                if (current_time - cache_time).seconds < self.cache_duration:
                    logger.debug(f"Using cached weather data for {location}")
                    return cached_data

            coords = await self.get_coordinates(location)
            if not coords:
                return None
            
            latitude, longitude = coords
            
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={latitude}&longitude={longitude}"
                f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
                f"&hourly=temperature_2m,weather_code"
                f"&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset"
                f"&temperature_unit=celsius&timezone=auto"
            )

            session = await SharedAsyncClient.get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Weather API returned status {response.status}")
                    return None
                data = await response.json()

            current = data.get('current', {})
            daily = data.get('daily', {})
            hourly = data.get('hourly', {})

            current_temp = current.get('temperature_2m')
            weather_code = current.get('weather_code', 0)
            condition = self.get_weather_condition(weather_code)
            humidity = current.get('relative_humidity_2m')
            wind_speed = current.get('wind_speed_10m')

            daily_max = daily.get('temperature_2m_max', [None])[0] if daily.get('temperature_2m_max') else None
            daily_min = daily.get('temperature_2m_min', [None])[0] if daily.get('temperature_2m_min') else None
            
            sunrise = daily.get('sunrise', [None])[0] if daily.get('sunrise') else None
            sunset = daily.get('sunset', [None])[0] if daily.get('sunset') else None
            
            if sunrise:
                sunrise_dt = datetime.fromisoformat(sunrise.replace('Z', '+00:00'))
                sunrise = sunrise_dt.strftime('%I:%M %p')
            if sunset:
                sunset_dt = datetime.fromisoformat(sunset.replace('Z', '+00:00'))
                sunset = sunset_dt.strftime('%I:%M %p')

            hourly_forecast = []
            if hourly.get('time') and hourly.get('temperature_2m') and hourly.get('weather_code'):
                current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
                start_index = 0
                
                for i, time_str in enumerate(hourly['time']):
                    try:
                        if time_str.endswith('Z'):
                            hour_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                        else:
                            hour_time = datetime.fromisoformat(time_str)
                        
                        if hour_time.tzinfo is not None:
                            hour_time = hour_time.replace(tzinfo=None)
                        
                        if hour_time >= current_hour:
                            start_index = i
                            break
                    except Exception as e:
                        logger.debug(f"Error parsing time {time_str}: {e}")
                        continue
                
                for i in range(start_index, min(start_index + 7, len(hourly['time']))):
                    try:
                        time_str = hourly['time'][i]
                        if time_str.endswith('Z'):
                            hour_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                        else:
                            hour_time = datetime.fromisoformat(time_str)
                        
                        if hour_time.tzinfo is not None:
                            hour_time = hour_time.replace(tzinfo=None)
                        
                        hour_condition = self.get_weather_condition(hourly['weather_code'][i])
                        temp = round(hourly['temperature_2m'][i])
                        formatted_time = hour_time.strftime('%I%p').lower().lstrip('0').replace('m', '')
                        
                        hourly_forecast.append(HourlyWeatherData(
                            time=formatted_time,
                            temperature=temp,
                            condition=hour_condition
                        ))
                    except Exception as e:
                        logger.error(f"Error processing hourly data: {e}")
                        continue

            weather_data = WeatherData(
                location=location.title(),
                date=datetime.now().strftime('%A, %B %d'),
                current_temperature=round(current_temp) if current_temp else 0,
                condition=condition,
                high_temperature=round(daily_max) if daily_max else 0,
                low_temperature=round(daily_min) if daily_min else 0,
                humidity=round(humidity) if humidity else None,
                wind_speed=round(wind_speed) if wind_speed else None,
                sunrise=sunrise,
                sunset=sunset,
                hourly_forecast=hourly_forecast,
                temperature_unit="°C",
                wind_unit="km/h"
            )

            self.cache[cache_key] = (weather_data, current_time)
            logger.info(f"Fetched weather for {location}: {current_temp}°C, {condition}")
            return weather_data

        except Exception as e:
            logger.error(f"Error fetching weather data for {location}: {e}")
            return None

class SheetDataProcessor:
    """Sheet data processor that calls the deployed Cloud Run function."""
    
    def __init__(self):
        self.base_url = config.base_url_sheets
        self.cache: Dict[str, tuple[Dict[str, Any], datetime]] = {}
        self.cache_duration = config.cache_duration_sheets
    
    async def get_customer_data(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer data from Google Sheets via Cloud Run function."""
        try:
            # Check cache first
            cache_key = f"customer_{customer_id}"
            current_time = datetime.now()
            
            if cache_key in self.cache:
                cached_data, cache_time = self.cache[cache_key]
                if (current_time - cache_time).seconds < self.cache_duration:
                    logger.debug(f"Using cached data for customer {customer_id}")
                    return cached_data
            
            # Make API call to Cloud Run function
            session = await SharedAsyncClient.get_session()
            params = {"customer_id": customer_id}
            headers = {"Content-Type": "application/json"}
            
            async with session.get(
                self.base_url, 
                params=params, 
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Cache the result
                    self.cache[cache_key] = (data, current_time)
                    logger.info(f"Fetched customer data for ID: {customer_id}")
                    return data
                elif response.status == 404:
                    logger.warning(f"Customer ID {customer_id} not found")
                    return None
                else:
                    error_text = await response.text()
                    logger.error(f"API returned {response.status}: {error_text}")
                    return None
                        
        except Exception as e:
            logger.error(f"Error fetching customer data for {customer_id}: {e}")
            return None

# Global instances
weather_processor = WeatherDataProcessor()  
market_price_processor = MarketPriceProcessor()
sheet_processor = SheetDataProcessor()