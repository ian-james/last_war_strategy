"""
Last War Scheduler - Strategic planning tool for Last War game events
Refactored modular version
"""

import streamlit as st
import os
import sys
from pathlib import Path

# Add src directory to Python path for imports
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import utilities
from app.utils.time_utils import setup_timezone_and_time
from app.utils.data_loaders import get_game_data, get_special_events
from app.utils.task_manager import cleanup_expired_tasks

# Import page modules
from app.pages import (
    dashboard,
    weekly_calendar,
    arms_scheduler,
    vs_duel,
    special_events,
    daily_tasks,
    calculator,
    secretary_buffs,
)

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Last Standing Tactician",
    layout="wide",
    page_icon="🛡️"
)

# --- ENSURE DATA DIRECTORY EXISTS ---
if not os.path.exists("data"):
    os.makedirs("data")

# --- SIDEBAR SETUP ---
st.sidebar.title("🛡️ Command Center")

# Dashboard quick access button (except on Dashboard itself)
with st.sidebar:
    if st.session_state.get('nav_page', "Main Dashboard") != "Main Dashboard":
        if st.button("🏠 Dashboard", use_container_width=True, type="primary"):
            st.session_state['nav_page'] = "Main Dashboard"
            st.rerun()

# --- TIME SETUP ---
time_ctx = setup_timezone_and_time()

# --- LOAD DATA ---
df = get_game_data()
specials_df = get_special_events()
cleanup_expired_tasks()

# --- NAVIGATION ---
page = st.sidebar.selectbox(
    "Navigate",
    [
        "Main Dashboard",
        "Weekly 2× Calendar",
        "Arms Race Scheduler",
        "VS Duel Manager",
        "Special Events Manager",
        "Secretary Buffs",
        "Daily Tasks Manager",
        "Speed-Up Calculator"
    ],
    key="nav_page"
)

# --- PAGE ROUTING ---
if page == "Main Dashboard":
    dashboard.render(time_ctx, df, specials_df)

elif page == "Weekly 2× Calendar":
    weekly_calendar.render(time_ctx, df)

elif page == "Arms Race Scheduler":
    arms_scheduler.render(time_ctx, df)

elif page == "VS Duel Manager":
    vs_duel.render(time_ctx, df)

elif page == "Special Events Manager":
    special_events.render(time_ctx, specials_df)

elif page == "Secretary Buffs":
    secretary_buffs.render(time_ctx)

elif page == "Daily Tasks Manager":
    daily_tasks.render(time_ctx)

elif page == "Speed-Up Calculator":
    calculator.render(time_ctx)
