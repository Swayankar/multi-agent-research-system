"""
FastAPI web UI for the multi-agent research pipeline.

Run with:
    uvicorn app:app --reload

This file must sit in the SAME folder as pipeline.py, agents.py and tools.py
(i.e. copy it into your existing project folder next to those files).
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pipeline import run_research_pipeline

# ---------------------------------------------------------------------------
# Resolve paths relative to THIS file, not the current working directory.
# This is what was causing the earlier "template not found" style errors --
# uvicorn's cwd depends on where you launch it from, so hardcoding
# "templates/" as a relative path is fragile. Path(__file__) fixes that.
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Multi-Agent Research Pipeline")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

STEP_ORDER = ["search", "scrape", "write", "critique"]


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.websocket("/ws/research")
async def research_ws(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_event_loop()

    try:
        raw = await websocket.receive_text()
        payload = json.loads(raw)
        topic = (payload.get("topic") or "").strip()

        if not topic:
            await websocket.send_json({"type": "error", "message": "Please enter a research topic."})
            return

        queue: asyncio.Queue = asyncio.Queue()

        # run_research_pipeline is synchronous and calls this callback from a
        # worker thread (via run_in_executor below), so we hop back onto the
        # event loop thread with call_soon_threadsafe before touching the queue.
        def progress_callback(step_key: str, status: str, data: Optional[str] = None):
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "step", "step": step_key, "status": status, "data": data},
            )

        async def run_pipeline_task():
            try:
                result = await loop.run_in_executor(
                    None, run_research_pipeline, topic, progress_callback
                )
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {
                        "type": "complete",
                        "report": result.get("report", ""),
                        "feedback": result.get("feedback", ""),
                    },
                )
            except Exception as exc:  # surface pipeline errors to the browser
                loop.call_soon_threadsafe(
                    queue.put_nowait, {"type": "error", "message": str(exc)}
                )

        pipeline_task = asyncio.ensure_future(run_pipeline_task())

        while True:
            msg = await queue.get()
            await websocket.send_json(msg)
            if msg["type"] in ("complete", "error"):
                break

        await pipeline_task

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass