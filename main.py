"""
FastAPI entrypoint — serves the chat UI and /chat API endpoint.
"""

import os
import uuid
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from agent.weather_agent import create_agent

app = FastAPI(title="Weather Agent")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ADK setup
session_service = InMemorySessionService()
APP_NAME = "weather_agent_app"

# Session store: maps session_id -> (user_id, session_id)
_sessions: dict[str, tuple[str, str]] = {}


def get_or_create_session(session_id: str) -> tuple[str, str]:
    if session_id not in _sessions:
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        asyncio.get_event_loop().run_until_complete(
            session_service.create_session(
                app_name=APP_NAME, user_id=user_id, session_id=session_id
            )
        )
        _sessions[session_id] = (user_id, session_id)
    return _sessions[session_id]


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = os.path.join(static_dir, "index.html")
    with open(html_path) as f:
        return HTMLResponse(content=f.read())


@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        user_id, sid = get_or_create_session(req.session_id)
        agent = create_agent()
        runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

        user_msg = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=req.message)]
        )

        reply_parts = []
        async for event in runner.run_async(
            user_id=user_id,
            session_id=sid,
            new_message=user_msg,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        reply_parts.append(part.text)

        reply = "".join(reply_parts) or "Sorry, I couldn't get a response. Please try again."
        return JSONResponse({"reply": reply})

    except Exception as e:
        return JSONResponse({"reply": f"Error: {str(e)}"}, status_code=500)


@app.get("/health")
async def health():
    return {"status": "ok"}