"""Special Events Manager page."""

import os
import streamlit as st
import pandas as pd
import pendulum
from app.config.constants import SPECIAL_FILE
from app.utils.data_loaders import get_special_events


def render(time_ctx: dict):
    """Render the Special Events Manager page.

    Args:
        time_ctx: Dictionary from setup_timezone_and_time() containing:
            - now_utc: Current time in UTC
            - now_server: Current time in server timezone
            - user_tz: User's selected timezone
            - user_tz_label: Label for user's timezone
            - fmt: Time format string
    """
    now_utc = time_ctx['now_utc']
    now_server = time_ctx['now_server']
    user_tz = time_ctx['user_tz']
    user_tz_label = time_ctx['user_tz_label']
    fmt = time_ctx['fmt']

    st.title("📅 Special Events Manager")
    RESTORE_SPECIAL = "data/restore_special_events.csv"
    specials_df = get_special_events()

    if 'edit_event' not in st.session_state:
        st.session_state.edit_event = None

    col_header, col_actions = st.columns([4, 2])
    with col_actions:
        c_clear, c_restore = st.columns(2)
        if c_clear.button("🧹 Clear Fields", use_container_width=True):
            st.session_state.edit_event = None
            st.rerun()
        if c_restore.button("🔄 Restore Defaults", use_container_width=True):
            if os.path.exists(RESTORE_SPECIAL):
                pd.read_csv(RESTORE_SPECIAL, sep="\t").to_csv(SPECIAL_FILE, sep="\t", index=False)
                st.rerun()

    with st.form("event_editor"):
        edit = st.session_state.edit_event
        st.write("### 📝 Edit Event" if edit else "### ➕ Add New Event")
        c1, c2, c3 = st.columns([2, 2, 1])
        name = c1.text_input("Event Name", value=edit['name'] if edit else "")
        days = c2.multiselect("Days Active", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], default=edit['days'].split(',') if edit else [])
        freq = c3.selectbox("Frequency", ["weekly", "biweekly"], index=0 if not edit else (0 if edit['freq'] == 'weekly' else 1))

        current_parity = now_utc.week_of_year % 2
        c4, c5, c6 = st.columns(3)
        starts_this_week = c4.selectbox("Starts this week?", ["Yes", "No"], index=0 if not edit or (int(edit['ref_week']) % 2 == current_parity) else 1) if freq == "biweekly" else "Yes"

        # Check if event is all-day (02:00 to 01:59 server time)
        is_all_day_default = False
        init_s, init_e = "12:00", "14:00"
        if edit:
            try:
                if edit['start_time'] == "02:00" and edit['end_time'] == "01:59":
                    is_all_day_default = True
                sh, sm = map(int, edit['start_time'].split(':'))
                eh, em = map(int, edit['end_time'].split(':'))
                init_s = now_server.at(sh, sm).in_timezone(user_tz).format("HH:mm")
                init_e = now_server.at(eh, em).in_timezone(user_tz).format("HH:mm")
            except:
                pass

        all_day = c4.checkbox("All Day Event", value=is_all_day_default, help="Event runs for the full game day (02:00 to 01:59 server time)")

        if all_day:
            st.info("ℹ️ All-day event will run from 02:00 to 01:59 server time (full game day cycle)")
            s_t, e_t = "02:00", "01:59"
        else:
            s_t = c5.text_input(f"Start Time ({user_tz_label})", value=init_s, disabled=all_day)
            e_t = c6.text_input(f"End Time ({user_tz_label})", value=init_e, disabled=all_day)

        if st.form_submit_button("💾 Save to File"):
            if name and days:
                final_ref = (current_parity if starts_this_week == "Yes" else 1 - current_parity) if freq == "biweekly" else 0
                if all_day:
                    s_utc, e_utc = "02:00", "01:59"
                else:
                    dummy = pendulum.today(user_tz)
                    s_utc = pendulum.parse(f"{dummy.format('YYYY-MM-DD')} {s_t}").set(tz=user_tz).in_timezone('UTC').format('HH:mm')
                    e_utc = pendulum.parse(f"{dummy.format('YYYY-MM-DD')} {e_t}").set(tz=user_tz).in_timezone('UTC').format('HH:mm')
                new_row = pd.DataFrame([{"name": name, "days": ",".join(days), "freq": freq, "ref_week": final_ref, "start_time": s_utc, "end_time": e_utc}])
                specials_df = pd.concat([specials_df[specials_df['name'] != name], new_row], ignore_index=True)
                specials_df.to_csv(SPECIAL_FILE, sep="\t", index=False)
                st.session_state.edit_event = None
                st.rerun()

    st.divider()
    st.subheader(f"📋 Configured Events ({len(specials_df)})")
    for idx, row in specials_df.iterrows():
        # Check if all-day event
        is_all_day = (str(row['start_time']) == "02:00" and str(row['end_time']) == "01:59")

        if is_all_day:
            time_display = "All Day"
        else:
            try:
                sh, sm = map(int, str(row['start_time']).split(':'))
                eh, em = map(int, str(row['end_time']).split(':'))
                l_s, l_e = now_server.at(sh, sm).in_timezone(user_tz).format(fmt), now_server.at(eh, em).in_timezone(user_tz).format(fmt)
                time_display = f"{l_s}-{l_e}"
            except:
                time_display = "N/A"

        with st.container(border=True):
            cols = st.columns([3, 4, 1, 1])
            cols[0].write(f"**{row['name']}**")
            status = "Active" if (row['freq'] == 'weekly' or (int(row['ref_week']) % 2 == current_parity)) else "Inactive"
            cols[1].write(f"🕒 {time_display} | 📅 {row['days']} | {row['freq']} ({status})")
            if cols[2].button("📝", key=f"ed_{idx}"):
                st.session_state.edit_event = row.to_dict()
                st.rerun()
            if cols[3].button("🗑️", key=f"dl_{idx}"):
                specials_df.drop(idx).to_csv(SPECIAL_FILE, sep="\t", index=False)
                st.rerun()
