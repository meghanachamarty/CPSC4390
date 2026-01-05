from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

from langchain.tools import tool
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from agentmanager import AgentManager

agent_manager = AgentManager("main-manager")

#------------------------------------------------------------------------------
# Tool for handling general course questions
#------------------------------------------------------------------------------
@tool
def general_tool(query: str) -> str:
    """
    Handle general course questions including:
    - Policy questions: late penalty, grade breakdown, drops allowed, collaboration rules, regrade window
    - Deadline questions: what's due this week/tomorrow/next
    - Resource lookup: where are lecture slides, project specs, etc.
    - Announcements: what are the new announcements since a certain date
    
    This tool searches course documents and returns relevant context. The AI will extract the answer from this context.
    """
    # Retrieve multiple relevant chunks (let Claude figure out which is most relevant)
    query_lower = query.lower()
    
    # For questions about "all classes" or "all my classes", get more chunks to find info across courses
    if any(phrase in query_lower for phrase in ['all my classes', 'all classes', 'all courses', 'for all', 'across all']):
        k = 15  # Get many chunks to find info from all courses
    # For assignment questions with numbers, get more chunks to ensure we find the right one
    elif any(word in query_lower for word in ['assignment', 'assn', 'hw', 'homework']) and any(char.isdigit() for char in query):
        k = 5
    else:
        k = 3  # Get 3 chunks for general questions
    
    # Use the vector store to find relevant chunks
    retrieved_docs = agent_manager.vector_store.similarity_search(query, k=k)
    
    if not retrieved_docs:
        return "I couldn't find relevant information in your course materials to answer this question."
    
    # Format all retrieved chunks with source info - let Claude extract what's needed
    context_parts = []
    for doc in retrieved_docs:
        source = doc.metadata.get('source', 'Unknown source')
        content = doc.page_content.strip()
        context_parts.append(f"From {source}:\n{content}")
    
    # Return all relevant context - Claude will extract the answer
    return "\n\n---\n\n".join(context_parts)

#------------------------------------------------------------------------------
# Construct the Agent with the general tool
#------------------------------------------------------------------------------

tools = [general_tool]
# If desired, specify custom instructions
# to do: refactor to force model to return a string
prompt = (
    "You are CourseKey, a helpful course assistant. You answer questions based on retrieved course documents and conversation history.\n\n"
    "CRITICAL RULES:\n"
    "- Use the retrieved context ONLY to find the answer - do NOT repeat or quote the context\n"
    "- Return ONLY your answer - nothing else, no sources, no context\n"
    "- Be extremely concise - 1-2 sentences maximum\n"
    "- Extract ONLY the information that directly answers the question\n"
    "- Use conversation history to understand follow-up questions (e.g., if user asks 'when is it due?' after asking about an assignment, refer to that assignment)\n\n"
    "INSTRUCTIONS:\n"
    "- Read the conversation history to understand context from previous messages\n"
    "- If the user asks a follow-up question (like 'when is it due?' or 'what about that?'), use the conversation history to understand what 'it' refers to\n"
    "- Read the retrieved document context carefully\n"
    "- If the user asks about 'all my classes' or 'all classes', provide information for ALL courses mentioned in the retrieved context\n"
    "- Find the specific information that answers the user's question\n"
    "- Answer directly and concisely - only what was asked\n"
    "- For yes/no questions, start with 'Yes' or 'No', then one sentence if needed\n"
    "- Use plain text only - no markdown, no formatting\n"
    "- If context has multiple items (like multiple assignments or courses), provide information for all relevant items when asked\n\n"
    "EXAMPLES:\n"
    "Q: 'Can I work with classmates on an assignment?'\n"
    "A: 'Yes, you can discuss concepts with classmates, but you must write all code yourself.'\n\n"
    "Q: 'when is Assignment 3 due?'\n"
    "A: 'Assignment 3 is due November 5, 2025 at 11:59 PM.'\n\n"
    "Q (follow-up): 'when is it due?' (after asking about Assignment 3)\n"
    "A: 'Assignment 3 is due November 5, 2025 at 11:59 PM.'\n\n"
    "IMPORTANT: Your response should ONLY contain your answer. Do NOT include any retrieved context, sources, or extra information.\n"
    "Use general_tool to retrieve course documents when needed, then return ONLY your concise answer.\n"
    "Always return text as a string."
)

my_ai_agent = create_agent(agent_manager.llm, tools, system_prompt=prompt)


#------------------------------------------------------------------------------
# Scheduler Agent - builds structured study plans from todo inputs
#------------------------------------------------------------------------------

def _coerce_payload(payload: Any) -> Dict[str, Any]:
    """Normalize tool input which may arrive as dict, stringified JSON, or text."""
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {"raw_request": payload}
    return {"raw_request": str(payload)}


def _parse_date(value: Any) -> datetime:
    """Parse a date/datetime string into a date; fallback to today's date."""
    if isinstance(value, datetime):
        return value
    if value is None:
        return datetime.utcnow()
    if isinstance(value, (int, float)):
        return datetime.utcfromtimestamp(value)

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return datetime.utcnow()


def _priority_weight(priority: str | None) -> float:
    mapping = {
        "urgent": 3.0,
        "high": 2.5,
        "medium": 2.0,
        "normal": 1.5,
        "low": 1.0,
    }
    if not priority:
        return 1.5
    return mapping.get(priority.lower(), 1.5)


@tool
def scheduler_tool(request: dict | str) -> str:
    """
    Convert a todo payload into structured scheduling context.

    Expects payload keys:
    - todos: list of tasks (title, due_date, estimated_hours, priority, course)
    - week_start: optional ISO date to anchor the weekly plan
    - user_preferences: dict of preferred_days, daily_time_blocks, max_hours_per_day,
      study_block_minutes, notification_channels, reminder_offsets
    """

    payload = _coerce_payload(request)

    todos: List[Dict[str, Any]] = payload.get("todos", [])
    if not todos:
        return json.dumps(
            {
                "message": "No todo items were provided, so no plan can be generated.",
                "received": payload,
            },
            indent=2,
        )

    week_start_raw = payload.get("week_start")
    week_start = _parse_date(week_start_raw).date()
    preferences: Dict[str, Any] = payload.get("user_preferences", {}) or {}

    max_hours = float(preferences.get("max_hours_per_day", 4))
    block_minutes = int(preferences.get("study_block_minutes", 60) or 60)
    block_hours = max(block_minutes / 60, 0.5)
    preferred_days = {day.lower() for day in preferences.get("preferred_days", []) or []}
    time_blocks = preferences.get("daily_time_blocks") or [
        "08:00-10:00",
        "14:00-16:00",
        "19:00-21:00",
    ]
    reminder_offsets = preferences.get("reminder_offsets") or [3, 1]
    reminder_channels = preferences.get("notification_channels") or ["push"]

    normalized_tasks: List[Dict[str, Any]] = []
    for task in todos:
        title = task.get("title") or task.get("name") or "Untitled Task"
        due_date = _parse_date(task.get("due_date") or task.get("deadline") or week_start)
        normalized_tasks.append(
            {
                "title": title,
                "course": task.get("course"),
                "due_date": due_date.date(),
                "estimated_hours": max(float(task.get("estimated_hours", 2) or 2), 0.5),
                "priority": task.get("priority", "medium"),
                "weight": _priority_weight(task.get("priority")),
                "category": task.get("category"),
                "notes": task.get("notes"),
            }
        )

    normalized_tasks.sort(key=lambda x: (x["due_date"], -x["weight"], -x["estimated_hours"]))

    week_days = [week_start + timedelta(days=i) for i in range(7)]
    day_plans: List[Dict[str, Any]] = []
    for day in week_days:
        day_plans.append(
            {
                "date": day,
                "day_name": day.strftime("%A"),
                "total_hours": 0.0,
                "capacity": max_hours,
                "blocks": [],
            }
        )

    allocations: Dict[int, Dict[str, Any]] = {
        idx: {"blocks": [], "scheduled_hours": 0.0, "remaining": task["estimated_hours"]}
        for idx, task in enumerate(normalized_tasks)
    }

    def _day_allowed(day_name: str) -> bool:
        if not preferred_days:
            return True
        return day_name.lower() in preferred_days

    for idx, task in enumerate(normalized_tasks):
        hours_remaining = task["estimated_hours"]
        for plan in day_plans:
            if hours_remaining <= 0:
                break
            if plan["date"] > task["due_date"]:
                continue
            if plan["total_hours"] >= plan["capacity"]:
                continue
            if not _day_allowed(plan["day_name"]):
                continue

            available = plan["capacity"] - plan["total_hours"]
            block = min(hours_remaining, block_hours, available)
            if block <= 0:
                continue

            time_block_label = time_blocks[len(plan["blocks"]) % len(time_blocks)]
            plan["blocks"].append(
                {
                    "task": task["title"],
                    "course": task["course"],
                    "hours": round(block, 2),
                    "time_block": time_block_label,
                    "priority": task["priority"],
                }
            )
            plan["total_hours"] += block

            allocations[idx]["blocks"].append(
                {
                    "day": plan["day_name"],
                    "date": plan["date"].isoformat(),
                    "hours": round(block, 2),
                    "time_block": time_block_label,
                }
            )
            allocations[idx]["scheduled_hours"] += block
            allocations[idx]["remaining"] = max(0.0, allocations[idx]["remaining"] - block)
            hours_remaining -= block

    weekly_distribution = [
        {
            "day": plan["day_name"],
            "date": plan["date"].isoformat(),
            "total_hours": round(plan["total_hours"], 2),
            "capacity": plan["capacity"],
            "blocks": plan["blocks"],
        }
        for plan in day_plans
    ]

    task_summary = []
    at_risk = []
    for idx, task in enumerate(normalized_tasks):
        allocation = allocations[idx]
        entry = {
            "title": task["title"],
            "course": task["course"],
            "due_date": task["due_date"].isoformat(),
            "priority": task["priority"],
            "estimated_hours": task["estimated_hours"],
            "scheduled_hours": round(allocation["scheduled_hours"], 2),
            "remaining_hours": round(allocation["remaining"], 2),
            "scheduled_blocks": allocation["blocks"],
        }
        task_summary.append(entry)
        if allocation["remaining"] > 0:
            at_risk.append(entry)

    today = datetime.utcnow().date()
    reminders: List[Dict[str, Any]] = []
    for task in normalized_tasks:
        notify_dates = []
        for offset in reminder_offsets:
            try:
                offset_int = int(offset)
            except (TypeError, ValueError):
                continue
            reminder_date = task["due_date"] - timedelta(days=offset_int)
            if reminder_date >= today:
                notify_dates.append(reminder_date.isoformat())
        reminders.append(
            {
                "task": task["title"],
                "due_date": task["due_date"].isoformat(),
                "notify_on": sorted(set(notify_dates)),
                "channels": reminder_channels,
                "message": f"Reminder to work on {task['title']} due {task['due_date'].isoformat()}.",
            }
        )

    heavy_days = [plan for plan in weekly_distribution if plan["total_hours"] >= plan["capacity"] * 0.8]
    light_days = [plan for plan in weekly_distribution if plan["total_hours"] <= plan["capacity"] * 0.4]

    plan_output = {
        "week_start": week_start.isoformat(),
        "weekly_distribution": weekly_distribution,
        "task_overview": task_summary,
        "study_block_recommendations": {
            "preferred_blocks": time_blocks,
            "block_length_hours": round(block_hours, 2),
            "notes": preferences.get(
                "study_notes",
                "Lean into higher-energy blocks early in the week and keep lighter reviews for lighter days.",
            ),
        },
        "reminders": reminders,
        "load_highlights": {
            "heavy_days": heavy_days,
            "light_days": light_days,
            "at_risk_items": at_risk,
        },
    }

    return json.dumps(plan_output, indent=2)


scheduler_prompt = (
    "You are CourseKey's Scheduler Agent. Your core task is to turn structured todo "
    "payloads into actionable weekly plans and timelines for students.\n\n"
    "Workflow:\n"
    "1. The user (or calling service) will provide JSON payloads that contain todos, week_start," \
    " and preferences.\n"
    "2. ALWAYS call scheduler_tool on that JSON to build the structured plan context.\n"
    "3. Read the tool output carefully and present a concise, helpful summary including:\n"
    "   - Weekly workload distribution (call out heavy/light days).\n"
    "   - Recommended study blocks tailored to their preferences.\n"
    "   - Reminder or notification suggestions tied to due dates.\n"
    "4. Provide clear next steps for the student.\n\n"
    "Guidelines:\n"
    "- Reference concrete dates and tasks whenever possible.\n"
    "- Show empathy for workload spikes and rebalance if needed.\n"
    "- Use short sections or bullet points; avoid markdown tables.\n"
    "- Never expose the raw JSON—only the synthesized plan.\n"
    "- If the tool response indicates missing data, explain what is needed.\n"
    "Always return text as a string."
)

scheduler_llm = init_chat_model("openai:gpt-4o-mini")

scheduler_agent = create_agent(
    scheduler_llm,
    [scheduler_tool],
    system_prompt=scheduler_prompt,
)
