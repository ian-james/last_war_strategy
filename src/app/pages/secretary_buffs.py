"""Secretary Buffs tracking page."""

import streamlit as st
import pendulum
from app.config.constants import SECRETARIES
from app.utils.secretary import get_secretary_event, save_secretary_event


def render(time_ctx: dict):
    """Render the Secretary Buffs page.

    Args:
        time_ctx: Dictionary from setup_timezone_and_time() containing:
            - user_tz: User's selected timezone
            - fmt: Time format string
            - now_server: Current time in server timezone
            - now_utc: Current time in UTC
    """
    user_tz = time_ctx['user_tz']
    fmt = time_ctx['fmt']
    now_server = time_ctx['now_server']
    now_utc = time_ctx['now_utc']

    st.title("🏛️ Secretary Buffs")
    st.caption("Track your timed secretary position. Each hold lasts 5 minutes — set the start time by server clock or queue depth.")

    sec_event = get_secretary_event()

    # --- Active buff banner (auto-clears on expiry) ---
    if sec_event:
        sec_start = pendulum.parse(sec_event['start_time_utc'])
        sec_end = pendulum.parse(sec_event['end_time_utc'])
        now_check = pendulum.now('UTC')

        if now_check >= sec_end:
            save_secretary_event(None)
            sec_event = None
            st.info("Previous secretary buff expired and was cleared.")
        else:
            sec_type = sec_event['type']
            bonuses = SECRETARIES[sec_type]['bonuses']
            icon = SECRETARIES[sec_type]['icon']

            if now_check < sec_start:
                status_str = f"Starts at {sec_start.in_timezone(user_tz).format(fmt)}"
                status_color = "#1976d2"
            else:
                status_str = f"Ends at {sec_end.in_timezone(user_tz).format(fmt)}"
                status_color = "#2e7d32"

            bonus_tags = "  ".join(
                f'<span style="background:#c8e6c9; padding:3px 10px; border-radius:12px; '
                f'font-size:0.9em; color:#2e7d32; font-weight:bold;">{name} {val}</span>'
                for name, val in bonuses
            )

            st.html(f"""
                <div style="background:#e8f5e9; border:2px solid #4caf50; border-radius:10px;
                            padding:18px; margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <h3 style="margin:0; color:#1b5e20;">{icon} {sec_type}</h3>
                            <div style="color:{status_color}; font-weight:bold; font-size:1.15em; margin-top:6px;">{status_str}</div>
                        </div>
                        <div style="text-align:right; color:#546e7a; font-size:0.9em;">
                            <div>Start: {sec_start.in_timezone(user_tz).format(fmt)}</div>
                            <div>End:&nbsp;&nbsp; {sec_end.in_timezone(user_tz).format(fmt)}</div>
                        </div>
                    </div>
                    <div style="margin-top:12px; display:flex; gap:6px; flex-wrap:wrap;">{bonus_tags}</div>
                </div>
            """, unsafe_allow_html=True)

            if st.button("🗑️ Clear active buff", type="secondary", key="sec_clear"):
                save_secretary_event(None)
                st.rerun()

            st.divider()

    # --- Secretary type selection ---
    with st.container(border=True):
        st.subheader("Choose Secretary")
        sec_type = st.selectbox(
            "Secretary Type",
            list(SECRETARIES.keys()),
            key="sec_type_select"
        )

        # Bonus preview
        sec_info = SECRETARIES[sec_type]
        bonus_cols = st.columns(len(sec_info['bonuses']))
        for col, (name, val) in zip(bonus_cols, sec_info['bonuses']):
            col.metric(name, val)

    # --- Time input ---
    with st.container(border=True):
        st.subheader("When does your turn start?")
        time_mode = st.radio(
            "Input method",
            ["Server Time", "People in Line"],
            key="sec_time_mode",
            horizontal=True
        )

        if time_mode == "Server Time":
            st.caption(f"Server clock now: {now_server.format('HH:mm:ss')}")
            tgt_cols = st.columns(2)
            srv_tgt_h = tgt_cols[0].number_input("Starts — Hour", min_value=0, max_value=23, value=now_server.hour, step=1, key="sec_srv_tgt_h")
            srv_tgt_m = tgt_cols[1].number_input("Starts — Minute", min_value=0, max_value=59, value=now_server.minute, step=1, key="sec_srv_tgt_m")

            # Delta from synced server clock; wraps forward at 24 h
            delta_minutes = (srv_tgt_h * 60 + srv_tgt_m) - (now_server.hour * 60 + now_server.minute)
            if delta_minutes < 0:
                delta_minutes += 1440
            sec_start_time = now_utc.add(minutes=delta_minutes)

            # Server-time end for preview (handle hour wrap)
            srv_end_total = srv_tgt_h * 60 + srv_tgt_m + 5
            server_preview = f"Server {srv_tgt_h:02d}:{srv_tgt_m:02d}–{(srv_end_total // 60) % 24:02d}:{srv_end_total % 60:02d}"
        else:
            people_ahead = st.number_input(
                "People ahead of you in line",
                min_value=0, value=0, step=1,
                key="sec_people_ahead",
                help="0 = you are up next (buff starts now)."
            )
            sec_start_time = now_utc.add(minutes=people_ahead * 5)
            server_preview = ""

        sec_end_time = sec_start_time.add(minutes=5)

        # Preview line
        st.info(
            f"**Buff window:**  "
            f"{sec_start_time.in_timezone(user_tz).format(fmt)} → {sec_end_time.in_timezone(user_tz).format(fmt)}  "
            + (f"({server_preview})" if server_preview else "")
        )

    # --- Activate ---
    if st.button("✅ Set Secretary Buff", type="primary", key="sec_set"):
        save_secretary_event({
            'type': sec_type,
            'start_time_utc': sec_start_time.to_iso8601_string(),
            'end_time_utc': sec_end_time.to_iso8601_string(),
        })
        st.success(
            f"{SECRETARIES[sec_type]['icon']} {sec_type} set!  "
            f"Active {sec_start_time.in_timezone(user_tz).format(fmt)}–{sec_end_time.in_timezone(user_tz).format(fmt)}."
        )
        st.rerun()
