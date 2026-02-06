"""Utility functions for the Last War Scheduler."""

from .helpers import word_in_text, format_duration, is_event_in_window
from .data_loaders import (
    get_game_data,
    get_special_events,
    get_daily_templates,
    get_active_tasks,
)
from .task_manager import (
    cleanup_expired_tasks,
    get_active_tasks_in_window,
    has_tasks_ending_in_window,
    get_daily_activation_count,
)
from .secretary import get_secretary_event, save_secretary_event
from .time_utils import setup_timezone_and_time

__all__ = [
    # helpers
    "word_in_text",
    "format_duration",
    "is_event_in_window",
    # data_loaders
    "get_game_data",
    "get_special_events",
    "get_daily_templates",
    "get_active_tasks",
    # task_manager
    "cleanup_expired_tasks",
    "get_active_tasks_in_window",
    "has_tasks_ending_in_window",
    "get_daily_activation_count",
    # secretary
    "get_secretary_event",
    "save_secretary_event",
    # time_utils
    "setup_timezone_and_time",
]
