"""
FastAPI entrypoint — serves the chat UI and /chat API endpoint.
"""

import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.weather_agent import run_agent

app = FastAPI(title="Weather Agent")

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


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
        reply = await run_agent(req.message)
        return JSONResponse({"reply": reply})
    except Exception as e:
        return JSONResponse({"reply": f"Error: {str(e)}"}, status_code=500)


@app.get("/health")
async def health():
    return {"status": "ok"}