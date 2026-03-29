"""
MCP Weather Server
Exposes a get_weather tool that fetches live data from Open-Meteo (free, no API key needed).
"""

import asyncio
import json
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

app = Server("weather-server")

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
        # Step 1: Geocode the city
        geo = await client.get(GEOCODE_URL, params={"name": city, "count": 1, "language": "en", "format": "json"})
        geo.raise_for_status()
        results = geo.json().get("results")
        if not results:
            return {"error": f"City '{city}' not found."}

        loc = results[0]
        lat, lon = loc["latitude"], loc["longitude"]
        name = loc["name"]
        country = loc.get("country", "")

        # Step 2: Fetch weather
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


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_weather",
            description="Get current weather for any city in the world.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name, e.g. 'Bengaluru' or 'Tokyo'",
                    }
                },
                "required": ["city"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "get_weather":
        raise ValueError(f"Unknown tool: {name}")

    city = arguments.get("city", "").strip()
    if not city:
        return [types.TextContent(type="text", text=json.dumps({"error": "City name is required."}))]

    data = await fetch_weather(city)
    return [types.TextContent(type="text", text=json.dumps(data))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
