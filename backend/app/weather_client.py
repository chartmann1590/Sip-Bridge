"""OpenWeatherMap client for weather information."""
import httpx
from typing import Optional, Dict
from .config import Config
import logging

logger = logging.getLogger(__name__)


class WeatherClient:
    """Client for interacting with OpenWeatherMap API."""

    BASE_URL = "https://api.openweathermap.org/data/2.5"

    def __init__(self):
        self.api_key = Config.OPENWEATHER_API_KEY

    def get_weather(self, location: str, units: str = "imperial") -> Optional[Dict]:
        """
        Get current weather for a location.

        Args:
            location: City name or "city,country_code" (e.g., "London", "London,UK")
            units: Temperature units - "imperial" (F), "metric" (C), or "standard" (K)

        Returns:
            Dictionary with weather data or None if request fails
        """
        if not self.api_key:
            logger.error("OpenWeatherMap API key not configured")
            return None

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.BASE_URL}/weather",
                    params={
                        "q": location,
                        "appid": self.api_key,
                        "units": units
                    }
                )

                if response.status_code == 200:
                    data = response.json()

                    # Extract key information
                    weather_info = {
                        "location": data.get("name", location),
                        "country": data.get("sys", {}).get("country", ""),
                        "temperature": data.get("main", {}).get("temp"),
                        "feels_like": data.get("main", {}).get("feels_like"),
                        "temp_min": data.get("main", {}).get("temp_min"),
                        "temp_max": data.get("main", {}).get("temp_max"),
                        "humidity": data.get("main", {}).get("humidity"),
                        "pressure": data.get("main", {}).get("pressure"),
                        "description": data.get("weather", [{}])[0].get("description", ""),
                        "main": data.get("weather", [{}])[0].get("main", ""),
                        "wind_speed": data.get("wind", {}).get("speed"),
                        "wind_deg": data.get("wind", {}).get("deg"),
                        "clouds": data.get("clouds", {}).get("all"),
                        "visibility": data.get("visibility"),
                        "units": units
                    }

                    logger.info(f"Weather fetched for {location}: {weather_info['temperature']}° {weather_info['description']}")
                    return weather_info
                elif response.status_code == 404:
                    logger.error(f"Location not found: {location}")
                    return None
                elif response.status_code == 401:
                    logger.error("Invalid OpenWeatherMap API key")
                    return None
                else:
                    logger.error(f"Weather API error: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return None

    def get_forecast(self, location: str, units: str = "imperial", cnt: int = 5) -> Optional[Dict]:
        """
        Get weather forecast for a location.

        Args:
            location: City name or "city,country_code"
            units: Temperature units - "imperial" (F), "metric" (C), or "standard" (K)
            cnt: Number of forecast entries (max 40, each 3 hours apart)

        Returns:
            Dictionary with forecast data or None if request fails
        """
        if not self.api_key:
            logger.error("OpenWeatherMap API key not configured")
            return None

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.BASE_URL}/forecast",
                    params={
                        "q": location,
                        "appid": self.api_key,
                        "units": units,
                        "cnt": cnt
                    }
                )

                if response.status_code == 200:
                    data = response.json()

                    forecast_list = []
                    for item in data.get("list", []):
                        forecast_list.append({
                            "datetime": item.get("dt_txt", ""),
                            "temperature": item.get("main", {}).get("temp"),
                            "feels_like": item.get("main", {}).get("feels_like"),
                            "temp_min": item.get("main", {}).get("temp_min"),
                            "temp_max": item.get("main", {}).get("temp_max"),
                            "description": item.get("weather", [{}])[0].get("description", ""),
                            "main": item.get("weather", [{}])[0].get("main", ""),
                            "humidity": item.get("main", {}).get("humidity"),
                            "wind_speed": item.get("wind", {}).get("speed"),
                        })

                    forecast_info = {
                        "location": data.get("city", {}).get("name", location),
                        "country": data.get("city", {}).get("country", ""),
                        "forecast": forecast_list,
                        "units": units
                    }

                    logger.info(f"Forecast fetched for {location}: {len(forecast_list)} entries")
                    return forecast_info
                else:
                    logger.error(f"Forecast API error: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching forecast: {e}")
            return None

    def format_weather_for_voice(self, weather_data: Dict) -> str:
        """
        Format weather data for voice response.

        Args:
            weather_data: Weather data dictionary from get_weather()

        Returns:
            Human-readable string suitable for text-to-speech
        """
        if not weather_data:
            return "I couldn't fetch the weather information."

        units_symbol = "°F" if weather_data.get("units") == "imperial" else "°C" if weather_data.get("units") == "metric" else "K"

        location = weather_data.get("location", "")
        country = weather_data.get("country", "")
        temp = weather_data.get("temperature")
        feels_like = weather_data.get("feels_like")
        description = weather_data.get("description", "")
        humidity = weather_data.get("humidity")
        wind_speed = weather_data.get("wind_speed")

        location_str = f"{location}, {country}" if country else location

        response = f"The weather in {location_str} is currently {description}. "
        response += f"The temperature is {temp}{units_symbol}"

        if feels_like and abs(temp - feels_like) > 3:
            response += f", but it feels like {feels_like}{units_symbol}"

        response += ". "

        if humidity:
            response += f"Humidity is {humidity}%. "

        if wind_speed:
            wind_unit = "miles per hour" if weather_data.get("units") == "imperial" else "meters per second"
            response += f"Wind speed is {wind_speed} {wind_unit}."

        return response


# Global weather client instance
weather_client = WeatherClient()
