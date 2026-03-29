"""
Weather AI Agent — built with Google ADK + MCP
"""

import os
import asyncio
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters


def create_agent() -> Agent:
    """Create the ADK agent wired to our MCP weather server."""
    mcp_server_path = os.path.join(os.path.dirname(__file__), "..", "mcp_server", "weather_server.py")
    mcp_server_path = os.path.abspath(mcp_server_path)

    toolset = MCPToolset(
        connection_params=StdioServerParameters(
            command="python",
            args=[mcp_server_path],
        )
    )

    agent = Agent(
        name="weather_agent",
        model="gemini-2.0-flash",
        description="A helpful weather assistant that fetches real-time weather data for any city.",
        instruction="""You are a friendly weather assistant.

When the user asks about the weather in any city:
1. Use the get_weather tool to fetch current conditions.
2. Present the result in a warm, conversational way.
3. Include temperature (°C), feels-like, humidity, wind speed, and a short description.
4. Add a practical tip based on the conditions (e.g., carry an umbrella, stay hydrated).

If the city is not found, apologize and ask the user to try a different city name.
Always be concise and friendly.
""",
        tools=[toolset],
    )
    return agent