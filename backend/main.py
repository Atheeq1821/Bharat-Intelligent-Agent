"""
FastAPI backend for Bharat Intelligence Agent.

Endpoints:
  POST /chat
  POST /webhook/whatsapp
  GET  /history
  GET  /source-health
  GET  /health
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv(override=True)

from fastapi import BackgroundTasks, FastAPI, Form, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from twilio.rest import Client as TwilioClient
from twilio.twiml.messaging_response import MessagingResponse

from agent import run_agent
from coral_client import get_catalog_snapshot
from database import get_query_history


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _compute_source_health() -> dict[str, Any]:
    """
    Source reliability snapshot from coral.tables.
    """
    catalog, err = await get_catalog_snapshot()
    if err:
        return {
            "status": "error",
            "checked_at": _utc_now_iso(),
            "error": err,
            "source_count": 0,
            "table_count": 0,
            "sources": [],
        }

    sources: list[dict[str, Any]] = []
    table_count = 0
    for schema, tables in sorted(catalog.items()):
        count = len(tables)
        table_count += count
        sources.append(
            {
                "source": schema,
                "table_count": count,
                "status": "connected" if count > 0 else "empty",
            }
        )

    return {
        "status": "ok" if sources else "warning",
        "checked_at": _utc_now_iso(),
        "error": None,
        "source_count": len(sources),
        "table_count": table_count,
        "sources": sources,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.source_health = await _compute_source_health()
    yield


app = FastAPI(title="Bharat Intelligence Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_twilio = TwilioClient(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN"),
)
TWILIO_FROM = f"whatsapp:{os.getenv('TWILIO_PHONE_NUMBER', '')}"


class ChatRequest(BaseModel):
    message: str
    session_id: str = "web"


class ChatResponse(BaseModel):
    response: str
    chart: str | None = None
    sql: str | None = None
    sources_used: list[str] = []


@app.get("/health")
async def health():
    source_health = getattr(app.state, "source_health", {"status": "unknown"})
    return {"status": "ok", "sources": source_health.get("status", "unknown")}


@app.get("/source-health")
async def source_health(refresh: bool = Query(default=False)):
    if refresh or not hasattr(app.state, "source_health"):
        app.state.source_health = await _compute_source_health()
    return app.state.source_health


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        result = await run_agent(req.message, req.session_id)
        return ChatResponse(**result)
    except Exception as exc:
        msg = str(exc)
        lowered = msg.lower()
        if "credit balance is too low" in lowered:
            return ChatResponse(
                response=(
                    "The model provider rejected this request because the Anthropic credit "
                    "balance is too low. Please top up billing, then retry."
                ),
                chart=None,
                sql=None,
                sources_used=[],
            )
        if "rate limit" in lowered or "429" in lowered:
            return ChatResponse(
                response="Rate limit hit on the model provider. Please wait a moment and retry.",
                chart=None,
                sql=None,
                sources_used=[],
            )

        print(f"[chat] unhandled error: {exc}")
        return ChatResponse(
            response="The backend hit an unexpected error while generating the answer. Please retry.",
            chart=None,
            sql=None,
            sources_used=[],
        )


@app.get("/history")
async def history():
    rows = await get_query_history(limit=50)
    return {"history": rows}


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    background_tasks: BackgroundTasks,
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(default=""),
):
    background_tasks.add_task(_handle_whatsapp, From, Body)
    return Response(content=str(MessagingResponse()), media_type="application/xml")


async def _handle_whatsapp(from_number: str, body: str) -> None:
    result = await run_agent(body, session_id=from_number)
    reply_text = result["response"]

    msg_kwargs: dict[str, Any] = {
        "body": reply_text,
        "from_": TWILIO_FROM,
        "to": from_number,
    }

    chart = result.get("chart")
    if chart and isinstance(chart, str) and chart.startswith("http"):
        msg_kwargs["media_url"] = [chart]

    try:
        _twilio.messages.create(**msg_kwargs)
    except Exception as exc:
        print(f"[twilio] failed to send reply: {exc}")
