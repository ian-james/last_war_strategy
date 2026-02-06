"""Data loading functions for CSV and JSON files."""

import os
import pandas as pd
from app.config.constants import (
    DATA_FILE,
    ARMS_RACE_FILE,
    VS_DUEL_FILE,
    SPECIAL_FILE,
    DAILY_TEMPLATES_FILE,
    ACTIVE_TASKS_FILE,
)


def get_game_data():
    """Load and merge Arms Race and VS Duel schedules"""
    # Try loading from separate files first
    if os.path.exists(ARMS_RACE_FILE) and os.path.exists(VS_DUEL_FILE):
        arms_race_df = pd.read_csv(ARMS_RACE_FILE, sep="\t")
        # Type column should already exist in the file, but add it if missing
        if 'Type' not in arms_race_df.columns:
            arms_race_df['Type'] = 'Arms Race'

        vs_duel_df = pd.read_csv(VS_DUEL_FILE, sep="\t")
        vs_duel_df['Type'] = 'VS'
        vs_duel_df['Slot'] = 0

        # Merge both dataframes
        return pd.concat([arms_race_df, vs_duel_df], ignore_index=True)

    # Fallback to legacy file
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE, sep="\t")

    return pd.DataFrame(columns=["Day", "Type", "Slot", "Event", "Task", "Points"])


def get_special_events():
    """Load special events from CSV"""
    if os.path.exists(SPECIAL_FILE):
        return pd.read_csv(SPECIAL_FILE, sep="\t")
    return pd.DataFrame(columns=["name", "days", "freq", "ref_week", "start_time", "end_time"])


def get_daily_templates():
    """Load daily task templates from CSV"""
    if os.path.exists(DAILY_TEMPLATES_FILE):
        return pd.read_csv(DAILY_TEMPLATES_FILE, sep="\t")
    return pd.DataFrame(columns=[
        "name", "duration_n", "duration_r", "duration_sr",
        "duration_ssr", "duration_ur", "max_daily", "category",
        "color_code", "icon", "is_default"
    ])


def get_active_tasks():
    """Load active daily tasks from CSV"""
    if os.path.exists(ACTIVE_TASKS_FILE):
        return pd.read_csv(ACTIVE_TASKS_FILE, sep="\t")
    return pd.DataFrame(columns=[
        "task_id", "task_name", "start_time_utc",
        "duration_minutes", "end_time_utc", "status"
    ])
