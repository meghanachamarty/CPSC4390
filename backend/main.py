# run with: fastapi dev main.py

from __future__ import annotations

import json
import logging

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect, WebSocketState
from contextlib import asynccontextmanager

from ai_agent import agent_manager, my_ai_agent, scheduler_agent
from bandit.algorithm import get_bandit
import uvicorn


# ------------------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------------------
logger = logging.getLogger("coursekey")
logger.setLevel(logging.INFO)

# Only add handlers if none exist (avoid duplicates in reload / dev mode)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load mock course data
    print("🔄 Starting up CourseKey...")
    try:
        agent_manager.load_mock_course_data()
    except Exception as e:
        print(f"⚠️ Could not load mock data: {e}")
        print("⚠️ Vector store will be empty.")
    yield
    pass

app = FastAPI(lifespan=lifespan)

#------------------------------------------------------------------------------
# Allow your frontend origin
#------------------------------------------------------------------------------
origins = [
    "http://localhost:3000",
    # Allow requests from browser extensions (chrome-extension://, moz-extension://)
    # Note: Extension origins are dynamic, so we use allow_origin_regex
]

# allow CORS because frontend and backend are served on different ports
# Also allow browser extension requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://.*|chrome-extension://.*|moz-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#------------------------------------------------------------------------------
# Schemas
#------------------------------------------------------------------------------

class IngestUrlIn(BaseModel):
    url: str

class IngestTextIn(BaseModel):
    text: str
    metadata: dict | None = None

class AskIn(BaseModel):
    question: str

class BanditConversionIn(BaseModel):
    variant: str

class BanditStatsResponse(BaseModel):
    variant: str
    stats: dict


class TodoItem(BaseModel):
    title: str
    course: str | None = None
    due_date: str | None = None
    estimated_hours: float | None = None
    priority: str | None = None
    category: str | None = None
    notes: str | None = None


class StudyPreferences(BaseModel):
    preferred_days: list[str] | None = None
    daily_time_blocks: list[str] | None = None
    max_hours_per_day: float | None = None
    study_block_minutes: int | None = None
    notification_channels: list[str] | None = None
    reminder_offsets: list[int] | None = None
    study_notes: str | None = None
    timezone: str | None = None


class SchedulerPlanIn(BaseModel):
    todos: list[TodoItem]
    week_start: str | None = None
    user_preferences: StudyPreferences | None = None


class SchedulerPlanResponse(BaseModel):
    plan: str


#------------------------------------------------------------------------------
# Helper Functions
#------------------------------------------------------------------------------

def extract_text(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    # LangChain / multimodal: list of blocks
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                # common LC shape: {"type": "text", "text": "..."}
                if part.get("type") == "text":
                    parts.append(part.get("text", ""))
            elif isinstance(part, str):
                parts.append(part)
        return "".join(parts)
    # Fallback: stringify anything else
    return str(content)


#------------------------------------------------------------------------------
# Endpoints
#------------------------------------------------------------------------------
@app.get("/api")
async def root():
    return {"message": "Hello World"}


@app.get("/api/hello")
async def say_hello():
    return {"message": f"Hello There, Welcome To CourseKey! 📚"}

@app.get("/api/health")
async def health():
    return {"ok": True}

#------------------------------------------------------------------------------
# Multi-Armed Bandit Endpoints
#------------------------------------------------------------------------------

@app.get("/api/bandit/variant", response_model=BanditStatsResponse)
async def get_variant():
    """
    Get which button variant to show to the user.
    Uses epsilon-greedy bandit algorithm to balance exploration vs exploitation.
    """
    bandit = get_bandit()
    variant = bandit.select_variant()
    
    # Record impression (variant was shown)
    bandit.record_impression(variant)
    
    # Return variant and current stats
    stats = bandit.get_stats()
    return BanditStatsResponse(variant=variant, stats=stats)

@app.post("/api/bandit/conversion")
async def record_conversion(data: BanditConversionIn):
    """
    Record a button click (conversion) for a specific variant.
    This updates the bandit's estimates of which variant performs best.
    """
    bandit = get_bandit()
    bandit.record_conversion(data.variant)
    
    return {"status": "recorded", "variant": data.variant}

@app.get("/api/bandit/stats")
async def get_bandit_stats():
    """Get current statistics for all variants (for monitoring/debugging)."""
    bandit = get_bandit()
    stats = bandit.get_stats()
    best_variant = bandit.get_best_variant()
    
    return {
        "best_variant": best_variant,
        "stats": stats
    }

# ------------------------------------------------------------------------------
# REST Ask Endpoint (parallel to WebSocket /ws/ask)
# ------------------------------------------------------------------------------

@app.post("/api/ask")
async def rest_ask(payload: AskIn):
    """
    REST version of the ask endpoint.

    - Input: { "question": "..." }
    - Behavior: Runs my_ai_agent with a single-turn conversation and returns the
      final assistant response as JSON.
    - WebSocket endpoint /ws/ask remains unchanged; this is an additional option.
    """
    logger.info("📥 [REST /api/ask] Received request with question=%r", payload.question)

    # Minimal conversation history: single user message
    conversation_history = [
        {"role": "user", "content": payload.question}
    ]

    last = ""
    final_answer = ""

    try:
        # Stream from the agent, like in the WebSocket handler
        for event in my_ai_agent.stream(
            {"messages": conversation_history},
            stream_mode="values",
        ):
            msg = event["messages"][-1]

            # Works whether msg is an object or a dict
            content = getattr(msg, "content", None)
            if content is None and isinstance(msg, dict):
                content = msg.get("content")

            text = extract_text(content)
            if not text:
                logger.debug("🔎 [REST /api/ask] Empty or non-text frame, skipping.")
                continue

            # Heuristic to skip raw tool output (same as WebSocket)
            if (
                text.count("From ") > 1
                or (text.count("From ") == 1 and "---" in text and len(text) > 500)
                or ("Source: {" in text and "'source':" in text and "'document_type':" in text)
            ):
                logger.debug(
                    "🧰 [REST /api/ask] Skipping tool-like output frame: %.80r...",
                    text,
                )
                continue

            # Track the evolving answer (for debugging / future streaming)
            if text.startswith(last):
                delta = text[len(last):]
            else:
                delta = text

            logger.debug("✏️ [REST /api/ask] Delta chunk: %.80r...", delta)
            last = text
            final_answer = text

        if not final_answer:
            logger.warning(
                "⚠️ [REST /api/ask] Finished streaming but final_answer is empty."
            )
            # Optional: return a 502 to signal upstream issue
            raise HTTPException(
                status_code=502,
                detail="The AI agent did not produce a response.",
            )

        # Log the final answer (truncated)
        logger.info(
            "✅ [REST /api/ask] Completed successfully. Final answer (truncated): %.120r",
            final_answer,
        )

        # Optionally, you could append the assistant message to conversation_history
        # if you later want stateful REST conversations.
        conversation_history.append({"role": "assistant", "content": final_answer})

        return {"answer": final_answer}

    except HTTPException:
        logger.exception("🚫 [REST /api/ask] HTTPException raised.")
        raise
    except Exception as e:
        logger.exception("❌ [REST /api/ask] Unexpected error: %s", e)
        # Generic 500 response to client
        raise HTTPException(
            status_code=500,
            detail="Internal server error while processing your question.",
        )



@app.post("/api/scheduler/plan", response_model=SchedulerPlanResponse)
async def generate_scheduler_plan(payload: SchedulerPlanIn):
    """Create a weekly action plan via the scheduler agent."""
    if not payload.todos:
        raise HTTPException(status_code=400, detail="Please provide at least one todo item.")

    scheduler_payload = payload.model_dump(exclude_none=True)
    payload_json = json.dumps(scheduler_payload, default=str)

    logger.info(
        "📆 [REST /api/scheduler/plan] Todos=%d, week_start=%s",
        len(payload.todos),
        payload.week_start,
    )

    conversation_history = [
        {
            "role": "user",
            "content": (
                "Generate a 7-day plan with weekly workload distribution, study blocks,"
                " and reminder suggestions.\n"
                "Call scheduler_tool using the JSON payload inside <payload> tags before"
                " responding.\n"
                "<payload>\n"
                f"{payload_json}\n"
                "</payload>"
            ),
        }
    ]

    last = ""
    final_answer = ""

    try:
        for event in scheduler_agent.stream(
            {"messages": conversation_history},
            stream_mode="values",
        ):
            msg = event["messages"][-1]
            content = getattr(msg, "content", None)
            if content is None and isinstance(msg, dict):
                content = msg.get("content")

            text = extract_text(content)
            if not text:
                continue

            if (
                text.count("From ") > 1
                or (text.count("From ") == 1 and "---" in text and len(text) > 500)
                or ("Source: {" in text and "'source':" in text and "'document_type':" in text)
            ):
                continue

            if text.startswith(last):
                last = text
                final_answer = text
                continue

            last = text
            final_answer = text

        if not final_answer:
            raise HTTPException(
                status_code=502,
                detail="The scheduler agent did not produce a response.",
            )

        logger.info(
            "✅ [REST /api/scheduler/plan] Completed successfully. Final answer (truncated): %.120r",
            final_answer,
        )

        return SchedulerPlanResponse(plan=final_answer)

    except HTTPException:
        logger.exception("🚫 [REST /api/scheduler/plan] HTTPException raised.")
        raise
    except Exception as exc:
        logger.exception("❌ [REST /api/scheduler/plan] Unexpected error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Internal server error while creating the schedule.",
        )




if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8011, reload=True)
