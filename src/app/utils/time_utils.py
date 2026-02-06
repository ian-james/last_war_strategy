"""Timezone and time calculation utilities."""

import streamlit as st
import pendulum
from pendulum.tz import FixedTimezone
from app.config.constants import SLOT_START_HOURS


def setup_timezone_and_time():
    """Setup timezone selectors and calculate current time values.

    This function renders the sidebar timezone configuration and calculates
    all time-related values needed by the application.

    Returns:
        dict: Dictionary with keys:
            - server_tz: pendulum timezone object for server
            - server_tz_label: str label for server timezone (e.g., "UTC-2")
            - user_tz: pendulum timezone object or str for user's local timezone
            - user_tz_label: str label for user's timezone
            - fmt: str format string for time display ("HH:mm" or "h:mm A")
            - now_utc: pendulum DateTime in UTC
            - now_server: pendulum DateTime in server timezone
            - now_local: pendulum DateTime in user's timezone
            - current_slot: int (1-6) current slot number
            - active_start: pendulum DateTime of current slot start (server time)
            - game_day_start: pendulum DateTime of game day start (server midnight)
            - vs_day: str current day name for VS events
            - ar_day: str current day name for Arms Race events
    """
    with st.sidebar:
        st.header("⚙️ Configuration")

        # 0. Server Timezone (default UTC-2; persists once changed)
        _all_offsets = [f"UTC{'+' if h >= 0 else ''}{h}" for h in range(-12, 15)]
        _srv_offsets = ["UTC-2", "UTC+0"] + [o for o in _all_offsets if o not in ("UTC-2", "UTC+0")]
        _srv_sel = st.selectbox(
            "Server Timezone",
            _srv_offsets,
            index=0,
            key="server_tz_select",
        )
        _srv_hours = int(_srv_sel[3:])  # "UTC-2" → -2, "UTC+5" → 5
        server_tz = FixedTimezone(_srv_hours * 3600)
        server_tz_label = _srv_sel
        st.caption(f"Time in {_srv_sel}  |  UTC: {pendulum.now('UTC').format('HH:mm:ss')}")

        # 1. Local Timezone (defaults to server tz if not set)
        tz_options = [
            "Select Timezone (N/A)", "America/Halifax", "US/Eastern", "US/Central",
            "US/Mountain", "US/Pacific", "US/Alaska", "US/Hawaii",
            "Canada/Eastern", "Canada/Pacific",
            "Europe/London", "Europe/Paris", "Europe/Berlin",
            "Asia/Shanghai", "Asia/Tokyo", "Asia/Seoul",
            "Australia/Sydney", "UTC",
        ]
        selected_tz = st.selectbox("Local Timezone", tz_options, index=tz_options.index("America/Halifax"))

        if selected_tz == "Select Timezone (N/A)":
            user_tz = server_tz
            user_tz_label = server_tz_label
            st.info(f"💡 Defaulting to {server_tz_label}. Select your zone for local times.")
        else:
            user_tz = selected_tz
            user_tz_label = selected_tz

        # 2. Time Mode Selection
        time_mode = st.radio("Time Format", ["24h", "12h"], horizontal=True)
        fmt = "HH:mm" if time_mode == "24h" else "h:mm A"

    # Calculate current times
    now_utc = pendulum.now('UTC')
    now_server = pendulum.now(server_tz)  # game clock
    now_local = now_utc.in_timezone(user_tz)

    # Game day resets at midnight server time (= 22:00 Halifax time)
    vs_day = now_server.format('dddd')
    ar_day = now_server.format('dddd')

    # Current slot based on server time
    # Server boundaries: 00:00-04:00, 04:00-08:00, ..., 20:00-00:00
    current_slot = (now_server.hour // 4) + 1

    start_hour = SLOT_START_HOURS[current_slot - 1]

    # Start of the current 4-hour window in server time
    active_start = now_server.start_of('day').add(hours=start_hour)

    # Game day starts at midnight server time
    game_day_start = now_server.start_of('day')

    return {
        'server_tz': server_tz,
        'server_tz_label': server_tz_label,
        'user_tz': user_tz,
        'user_tz_label': user_tz_label,
        'fmt': fmt,
        'now_utc': now_utc,
        'now_server': now_server,
        'now_local': now_local,
        'current_slot': current_slot,
        'active_start': active_start,
        'game_day_start': game_day_start,
        'vs_day': vs_day,
        'ar_day': ar_day,
    }
