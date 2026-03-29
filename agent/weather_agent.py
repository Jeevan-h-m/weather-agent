"""
Weather Agent using Groq (free, no billing needed)
Manually calls the Open-Meteo API and uses Groq LLM to format the response.
"""

import os
import json
import httpx
from groq import Groq

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Heavy drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


async def fetch_weather(city: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        geo = await client.get(GEOCODE_URL, params={"name": city, "count": 1, "language": "en", "format": "json"})
        geo.raise_for_status()
        results = geo.json().get("results")
        if not results:
            return {"error": f"City '{city}' not found."}

        loc = results[0]
        lat, lon = loc["latitude"], loc["longitude"]
        name = loc["name"]
        country = loc.get("country", "")

        params = {
            "latitude": lat,
            "longitude": lon,
            "current": [
                "temperature_2m", "apparent_temperature", "relative_humidity_2m",
                "wind_speed_10m", "weathercode", "precipitation"
            ],
            "timezone": "auto",
        }
        wx = await client.get(WEATHER_URL, params=params)
        wx.raise_for_status()
        current = wx.json()["current"]

        code = current.get("weathercode", 0)
        return {
            "city": name,
            "country": country,
            "temperature_c": current["temperature_2m"],
            "feels_like_c": current["apparent_temperature"],
            "humidity_percent": current["relative_humidity_2m"],
            "wind_speed_kmh": current["wind_speed_10m"],
            "precipitation_mm": current["precipitation"],
            "condition": WMO_CODES.get(code, "Unknown"),
        }


async def run_agent(user_message: str) -> str:
    """Main agent function — fetches weather then asks Groq to format it."""
    groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    # Step 1: Extract city from user message
    extract = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": "Extract the city name from the user message. Reply with ONLY the city name, nothing else. If no city is mentioned, reply with NONE."
            },
            {"role": "user", "content": user_message}
        ],
        max_tokens=20,
    )
    city = extract.choices[0].message.content.strip()

    if city == "NONE" or not city:
        return "I'd be happy to help with weather! Please mention a city name, like 'What's the weather in Mumbai?'"

    # Step 2: Fetch weather via Open-Meteo (MCP tool logic)
    weather_data = await fetch_weather(city)

    if "error" in weather_data:
        return f"Sorry, I couldn't find weather data for '{city}'. Please try a different city name."

    # Step 3: Format friendly response with Groq
    weather_json = json.dumps(weather_data, indent=2)
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": """You are a friendly weather assistant.
Given weather JSON data, provide a warm conversational response including:
- Temperature and feels-like
- Weather condition
- Humidity and wind speed
- A practical tip (umbrella, sunscreen, jacket, etc.)
Keep it concise and friendly."""
            },
            {
                "role": "user",
                "content": f"Weather data:\n{weather_json}\n\nGive me a friendly weather report."
            }
        ],
        max_tokens=300,
    )

    return response.choices[0].message.content.strip()