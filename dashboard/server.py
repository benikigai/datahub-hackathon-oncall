"""FastAPI dashboard server for data-oncall.

Endpoints:
  GET  /                  → static HTML page
  GET  /static/<file>     → CSS / JS / JSON assets
  POST /trigger           → start an incident run (mutex: 409 if one already running)
  GET  /stream            → Server-Sent Events stream of run events
  POST /reset             → clear current run state

The dashboard reads `dashboard/static/finetune_metrics.json` on page load
to render the fine-tune story panel. Update that file with real numbers
when the LoRA training completes.
"""
import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse


STATIC_DIR = Path(__file__).parent / "static"

# In-memory run state — single run at a time
class RunState:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.current_run_id: str | None = None
        self.events: list[dict] = []
        self.subscribers: list[asyncio.Queue] = []
        self.completed: bool = False

    async def emit(self, event_dict: dict) -> None:
        """Append an event and broadcast to all subscribers."""
        self.events.append(event_dict)
        for q in list(self.subscribers):
            try:
                q.put_nowait(event_dict)
            except asyncio.QueueFull:
                pass

    def reset(self) -> None:
        self.current_run_id = None
        self.events = []
        self.completed = False
        # Don't drop subscribers — they'll get events from the next run


state = RunState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="data-oncall dashboard", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/trigger")
async def trigger(request: Request):
    body = await request.json()
    incident = body.get("incident", "").strip()
    use_stub = body.get("stub", False) or os.environ.get("DASHBOARD_USE_STUB") == "1"
    if not incident:
        raise HTTPException(status_code=400, detail="incident required")

    async with state.lock:
        if state.current_run_id and not state.completed:
            raise HTTPException(status_code=409, detail="another run in progress; POST /reset first")
        run_id = str(uuid.uuid4())[:8]
        state.current_run_id = run_id
        state.events = []
        state.completed = False

    # Kick off background runner
    asyncio.create_task(_run_in_background(run_id, incident, use_stub))
    return {"run_id": run_id, "status": "started"}


@app.post("/reset")
async def reset():
    state.reset()
    return {"ok": True}


@app.get("/stream")
async def stream():
    """Subscribe to the current run's event stream via SSE."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    state.subscribers.append(queue)

    # Replay any events already accumulated for the current run
    for e in state.events:
        try:
            queue.put_nowait(e)
        except asyncio.QueueFull:
            pass

    async def event_iter() -> AsyncIterator[dict]:
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Heartbeat to keep the connection alive
                    yield {"event": "ping", "data": "heartbeat"}
                    continue
                yield {"data": json.dumps(event)}
                if event.get("type") == "incident_complete":
                    # Send one final event then close
                    return
        finally:
            if queue in state.subscribers:
                state.subscribers.remove(queue)

    return EventSourceResponse(event_iter())


async def _run_in_background(run_id: str, incident: str, use_stub: bool):
    """Run the orchestrator (or stubs) and stream events."""
    async def emit(event):
        # Coerce Pydantic Event → dict
        if hasattr(event, "model_dump"):
            d = event.model_dump()
        else:
            d = event
        await state.emit(d)

    try:
        if use_stub:
            from dashboard.stub_agents import stub_run
            await stub_run(emit)
        else:
            from incident_response.orchestrator import run as orch_run
            await orch_run(incident, emit)
    except Exception as e:
        await state.emit({
            "ts": time.time(),
            "agent": "system",
            "type": "error",
            "data": {"message": f"orchestrator crashed: {e}"},
        })
    finally:
        state.completed = True


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "dashboard.server:app",
        host=os.environ.get("DASHBOARD_HOST", "127.0.0.1"),
        port=int(os.environ.get("DASHBOARD_PORT", 8001)),
        reload=False,
    )
