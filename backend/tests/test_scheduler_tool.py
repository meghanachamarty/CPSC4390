"""
Tests for the scheduler_tool function in ai_agent.py using the provided mock data.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("OPENAI_API_KEY", "test-key-openai")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-anthropic")

from unittest.mock import MagicMock

try:
    import langchain.agents as agents_module

    if not hasattr(agents_module, "create_agent"):
        def mock_create_agent(*args, **kwargs):
            return MagicMock()

        agents_module.create_agent = mock_create_agent
except (ImportError, AttributeError):
    mock_agents = MagicMock()
    mock_agents.create_agent = MagicMock(return_value=MagicMock())
    sys.modules["langchain.agents"] = mock_agents

import ai_agent 

ASSIGNMENTS_FILE = Path(__file__).resolve().parents[1] / "mock_data" / "assignments.txt"


def _assignment_from_mock_data(number: int) -> tuple[str, datetime]:
    """Return assignment title and due date parsed from mock_data/assignments.txt."""
    text = ASSIGNMENTS_FILE.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"Assignment {number}:\s*(?P<title>.+?)\r?\n- Due Date:\s*(?P<due>[^\r\n]+)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        raise AssertionError(f"Assignment {number} not found in mock data.")

    title = f"Assignment {number}: {match.group('title').strip()}"
    due_raw = match.group("due").strip()
    due_dt = datetime.strptime(due_raw, "%B %d, %Y, %I:%M %p")
    return title, due_dt


class TestSchedulerTool:
    """Scheduler agent planning tests based on mock assignments."""

    def test_scheduler_tool_builds_week_plan_from_mock_assignments(self):
        """Verify scheduler_tool builds a structured plan using mock assignments 3 and 4."""
        assignment_three, due_three = _assignment_from_mock_data(3)
        assignment_four, due_four = _assignment_from_mock_data(4)

        week_start = (due_three - timedelta(days=2)).date()
        payload = {
            "week_start": week_start.isoformat(),
            "todos": [
                {
                    "title": assignment_three,
                    "course": "CS 101",
                    "due_date": due_three.isoformat(),
                    "estimated_hours": 4,
                    "priority": "urgent",
                },
                {
                    "title": assignment_four,
                    "course": "CS 101",
                    "due_date": due_four.isoformat(),
                    "estimated_hours": 3,
                    "priority": "high",
                },
            ],
            "user_preferences": {
                "max_hours_per_day": 5,
                "study_block_minutes": 60,
                "preferred_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                "notification_channels": ["push", "email"],
                "reminder_offsets": [3, 1],
            },
        }

        raw_plan = ai_agent.scheduler_tool.run(payload)
        plan = json.loads(raw_plan)

        assert plan["week_start"] == week_start.isoformat()
        assert len(plan["weekly_distribution"]) == 7
        assert sum(day["total_hours"] for day in plan["weekly_distribution"]) > 0

        def _task_entry(title: str):
            return next((t for t in plan["task_overview"] if t["title"] == title), None)

        entry_three = _task_entry(assignment_three)
        entry_four = _task_entry(assignment_four)

        assert entry_three is not None
        assert entry_four is not None
        assert entry_three["due_date"] == due_three.date().isoformat()
        assert entry_four["due_date"] == due_four.date().isoformat()
        assert entry_three["scheduled_hours"] > 0
        assert entry_four["scheduled_hours"] > 0

        scheduled_tasks = {block["task"] for day in plan["weekly_distribution"] for block in day["blocks"]}
        assert assignment_three in scheduled_tasks
        assert assignment_four in scheduled_tasks

        reminder_titles = {rem["task"] for rem in plan["reminders"]}
        assert assignment_three in reminder_titles
        assert assignment_four in reminder_titles

    def test_scheduler_tool_respects_preferred_days_and_generates_reminders(self):
        """Ensure scheduler_tool honors preferred weekend study days and reminder defaults."""
        assignment_five, due_five = _assignment_from_mock_data(5)
        assignment_six, due_six = _assignment_from_mock_data(6)

        monday_before = (due_five - timedelta(days=due_five.weekday())).date()
        payload = {
            "week_start": monday_before.isoformat(),
            "todos": [
                {
                    "title": assignment_five,
                    "course": "CS 101",
                    "due_date": due_five.isoformat(),
                    "estimated_hours": 5,
                    "priority": "medium",
                },
                {
                    "title": assignment_six,
                    "course": "CS 101",
                    "due_date": due_six.isoformat(),
                    "estimated_hours": 4,
                    "priority": "high",
                },
            ],
            "user_preferences": {
                "preferred_days": ["Saturday", "Sunday"],
                "max_hours_per_day": 6,
                "study_block_minutes": 90,
                "notification_channels": ["push"],
                "reminder_offsets": [5, 2],
            },
        }

        raw_plan = ai_agent.scheduler_tool.run(payload)
        plan = json.loads(raw_plan)

        weekend_blocks = {
            day["day_name"]: list(day["blocks"])
            for day in plan["weekly_distribution"]
            if day["day_name"] in {"Saturday", "Sunday"}
        }
        weekday_blocks = [
            day for day in plan["weekly_distribution"] if day["day_name"] not in {"Saturday", "Sunday"}
        ]

        assert all(not day["blocks"] for day in weekday_blocks), "Weekday blocks should be empty."
        assert any(blocks for blocks in weekend_blocks.values()), "Weekend should contain scheduled blocks."

        reminder_map = {rem["task"]: rem for rem in plan["reminders"]}
        assert reminder_map[assignment_five]["channels"] == ["push"]
        assert reminder_map[assignment_six]["channels"] == ["push"]
        assert reminder_map[assignment_five]["due_date"] == due_five.date().isoformat()
        assert reminder_map[assignment_six]["due_date"] == due_six.date().isoformat()

        study_blocks = plan["study_block_recommendations"]
        assert study_blocks["block_length_hours"] == 1.5
        assert study_blocks["preferred_blocks"] == ["08:00-10:00", "14:00-16:00", "19:00-21:00"]
