"""Task management functions for active daily tasks."""

import os
import pandas as pd
import pendulum
from app.config.constants import ACTIVE_TASKS_FILE
from app.utils.data_loaders import get_active_tasks

ARMS_RACE_CATEGORIES = [
    "Base Building",
    "Tech Research",
    "Hero Advancement",
    "Unit Progression",
    "Drone Boost",
]


def cleanup_expired_tasks():
    """Remove tasks that have already ended from the active tasks file"""
    if not os.path.exists(ACTIVE_TASKS_FILE):
        return

    active_df = pd.read_csv(ACTIVE_TASKS_FILE, sep="\t")
    if active_df.empty:
        return

    now_utc_str = pendulum.now('UTC')
    valid_tasks = []
    for _, task in active_df.iterrows():
        end_time = pendulum.parse(str(task['end_time_utc']))
        if end_time > now_utc_str:
            valid_tasks.append(task)

    if valid_tasks:
        pd.DataFrame(valid_tasks).to_csv(ACTIVE_TASKS_FILE, sep="\t", index=False)
    else:
        pd.DataFrame(columns=[
            "task_id", "task_name", "start_time_utc",
            "duration_minutes", "end_time_utc", "status"
        ]).to_csv(ACTIVE_TASKS_FILE, sep="\t", index=False)


def get_active_tasks_in_window(start_utc, end_utc):
    """Get list of task names that are active during a time window

    Args:
        start_utc: pendulum DateTime in UTC
        end_utc: pendulum DateTime in UTC

    Returns:
        list: Task names that overlap with the window
    """
    active_df = get_active_tasks()
    if active_df.empty:
        return []

    active_in_window = []
    for _, task in active_df.iterrows():
        if str(task.get('status', 'active')) == 'completed':
            continue  # checkbox completions are not timed tasks
        task_start = pendulum.parse(str(task['start_time_utc']))
        task_end = pendulum.parse(str(task['end_time_utc']))

        # Check if task overlaps with window
        if task_start < end_utc and task_end > start_utc:
            active_in_window.append(str(task['task_name']))

    return active_in_window


def has_tasks_ending_in_window(start_utc, end_utc):
    """Check if any tasks end during this time window

    Args:
        start_utc: pendulum DateTime in UTC
        end_utc: pendulum DateTime in UTC

    Returns:
        bool: True if any task ends within the window
    """
    active_df = get_active_tasks()
    if active_df.empty:
        return False

    for _, task in active_df.iterrows():
        task_end = pendulum.parse(str(task['end_time_utc']))

        # Check if task ends within this window
        if start_utc <= task_end < end_utc:
            return True

    return False


def complete_checkbox_task(task_name, now_srv=None):
    """Mark a checkbox task as done for today.

    Stores a completion entry in active_daily_tasks.csv with duration=0
    and end_time aligned to the next daily task reset (02:00 server time).

    Args:
        task_name: Name of the checkbox task to complete
        now_srv: Current server time (pendulum DateTime). Used to compute
                 the correct expiry aligned with get_daily_activation_count.
    """
    active_df = get_active_tasks()
    now_utc_time = pendulum.now('UTC')

    if now_srv is not None:
        # Align expiry with daily task reset: next 02:00 server time
        next_reset_srv = now_srv.start_of('day').add(hours=2)
        if now_srv.hour >= 2:
            next_reset_srv = next_reset_srv.add(days=1)
        next_reset = next_reset_srv.in_timezone('UTC')
    else:
        # Fallback: 26 hours from now (safely covers any daily reset window)
        next_reset = now_utc_time.add(hours=26)

    task_id = f"{task_name}_{now_utc_time.int_timestamp}"

    new_entry = pd.DataFrame([{
        'task_id': task_id,
        'task_name': task_name,
        'start_time_utc': now_utc_time.to_iso8601_string(),
        'duration_minutes': 0,
        'end_time_utc': next_reset.to_iso8601_string(),
        'status': 'completed'
    }])

    active_df = pd.concat([active_df, new_entry], ignore_index=True)
    active_df.to_csv(ACTIVE_TASKS_FILE, sep="\t", index=False)


def is_checkbox_done_today(task_name, now_srv):
    """Check if a checkbox task has been completed today.

    Args:
        task_name: Name of the checkbox task
        now_srv: pendulum DateTime in server timezone

    Returns:
        bool: True if the task was completed since the last daily reset
    """
    return get_daily_activation_count(task_name, now_srv) > 0


def uncheck_task_today(task_name):
    """Remove today's completion entry for a checkbox task.

    Args:
        task_name: Name of the checkbox task to uncheck
    """
    active_df = get_active_tasks()
    if active_df.empty:
        return

    filtered = active_df[
        ~((active_df['task_name'] == task_name) & (active_df['status'] == 'completed'))
    ]
    filtered.to_csv(ACTIVE_TASKS_FILE, sep="\t", index=False)


def get_daily_activation_count(task_name, now_srv):
    """Count how many times a task was activated today (since last 02:00 server-time reset)

    Args:
        task_name: Base name of the task (without level suffix)
        now_srv: pendulum DateTime in server timezone

    Returns:
        int: Number of activations since daily reset
    """
    active_df = get_active_tasks()
    if active_df.empty:
        return 0

    # Calculate today's reset time (02:00 server time)
    daily_reset = now_srv.start_of('day').add(hours=2)
    if now_srv.hour < 2:
        daily_reset = daily_reset.subtract(days=1)

    # Count activations of this task since the reset
    count = 0
    for _, task in active_df.iterrows():
        # Remove level suffix from task name for counting (e.g., "Trucks (UR)" -> "Trucks")
        stored_name = str(task['task_name'])
        base_name = stored_name.split(' (')[0] if ' (' in stored_name else stored_name

        if stored_name == task_name or base_name == task_name:
            task_start = pendulum.parse(str(task['start_time_utc']))
            if task_start >= daily_reset:
                count += 1

    return count
