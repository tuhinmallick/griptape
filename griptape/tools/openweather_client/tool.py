from __future__ import annotations
from griptape.artifacts import ListArtifact, TextArtifact, ErrorArtifact, InfoArtifact
from griptape.tools import BaseTool
from griptape.utils.decorators import activity
from schema import Schema, Literal
from attr import define, field
import requests
import logging


@define
class OpenWeatherClient(BaseTool):
    BASE_URL = "https://api.openweathermap.org/data/3.0/onecall"
    GEOCODING_URL = "https://api.openweathermap.org/geo/1.0/direct"
    US_STATE_CODES = [
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DE",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NJ",
        "NM",
        "NY",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
    ]
    api_key: str = field(kw_only=True)
    units: str = field(default="imperial", kw_only=True)

    @activity(
        config={
            "description": "Can be used to fetch the latitude and longitude for a given location.",
            "schema": Schema(
                {
                    Literal(
                        "location",
                        description="Location to fetch coordinates for. "
                        "For US cities, use the format 'city_name, state_code'. "
                        "For non-US cities, use 'city_name, country_code'. "
                        "For cities without specifying state or country, simply use 'city_name'.",
                    ): str
                }
            ),
        }
    )
    def get_coordinates_by_location(self, params: dict) -> InfoArtifact | ErrorArtifact:
        location = params["values"].get("location")
        if coordinates := self._fetch_coordinates(location):
            lat, lon = coordinates
            return InfoArtifact(f"Coordinates for {location}: Latitude: {lat}, Longitude: {lon}")
        else:
            return ErrorArtifact(f"Error fetching coordinates for location: {location}")

    def _fetch_coordinates(self, location: str) -> tuple[float, float] | None:
        parts = location.split(",")
        if len(parts) == 2 and parts[1].strip() in self.US_STATE_CODES:
            location += ", US"
        request_params = {"q": location, "limit": 1, "appid": self.api_key}
        try:
            response = requests.get(self.GEOCODING_URL, params=request_params)
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list):
                    return data[0]["lat"], data[0]["lon"]
            else:
                logging.error(
                    f"Error fetching coordinates. HTTP Status Code: {response.status_code}. Response: {response.text}"
                )
        except Exception as e:
            logging.error(f"Error fetching coordinates: {e}")
        return None

    @activity(
        config={
            "description": "Can be used to fetch current weather data for a given location. "
            "Temperatures are returned in {{ _self.units }} by default.",
            "schema": Schema({Literal("location", description="Location to fetch weather data for."): str}),
        }
    )
    def get_current_weather_by_location(self, params: dict) -> ListArtifact | TextArtifact | ErrorArtifact:
        location = params["values"].get("location")
        if not (coordinates := self._fetch_coordinates(location)):
            return ErrorArtifact(f"Error fetching coordinates for location: {location}")
        lat, lon = coordinates
        request_params = {
            "lat": lat,
            "lon": lon,
            "exclude": "minutely,hourly,daily,alerts",
            "appid": self.api_key,
            "units": self.units,
        }
        return self._fetch_weather_data(request_params)

    @activity(
        config={
            "description": "Can be used to fetch hourly forecast for a given location up to 48 hours ahead. "
            "Temperatures are returned in {{ _self.units }} by default.",
            "schema": Schema({Literal("location", description="Location to fetch hourly forecast for."): str}),
        }
    )
    def get_hourly_forecast_by_location(self, params: dict) -> ListArtifact | TextArtifact | ErrorArtifact:
        location = params["values"].get("location")
        if not (coordinates := self._fetch_coordinates(location)):
            return ErrorArtifact(f"Error fetching coordinates for location: {location}")
        lat, lon = coordinates
        request_params = {
            "lat": lat,
            "lon": lon,
            "exclude": "minutely,current,daily,alerts",
            "appid": self.api_key,
            "units": self.units,
        }
        return self._fetch_weather_data(request_params)

    @activity(
        config={
            "description": "Can be used to fetch daily forecast for a given location up to 8 days ahead. "
            "Temperatures are returned in {{ _self.units }} by default.",
            "schema": Schema({Literal("location", description="Location to fetch daily forecast for."): str}),
        }
    )
    def get_daily_forecast_by_location(self, params: dict) -> ListArtifact | TextArtifact | ErrorArtifact:
        location = params["values"].get("location")
        if not (coordinates := self._fetch_coordinates(location)):
            return ErrorArtifact(f"Error fetching coordinates for location: {location}")
        lat, lon = coordinates
        request_params = {
            "lat": lat,
            "lon": lon,
            "exclude": "minutely,hourly,current,alerts",
            "appid": self.api_key,
            "units": self.units,
        }
        return self._fetch_weather_data(request_params)

    def _fetch_weather_data(self, request_params: dict) -> ListArtifact | TextArtifact | ErrorArtifact:
        try:
            response = requests.get(self.BASE_URL, params=request_params)
            if response.status_code == 200:
                data = response.json()
                if not isinstance(data, list):
                    return TextArtifact(str(data))
                wrapped_data = [InfoArtifact(item) for item in data]
                return ListArtifact(wrapped_data)
            else:
                logging.error(f"Error fetching weather data. HTTP Status Code: {response.status_code}")
                return ErrorArtifact("Error fetching weather data from OpenWeather API")
        except Exception as e:
            logging.error(f"Error fetching weather data: {e}")
            return ErrorArtifact(f"Error fetching weather data: {e}")
