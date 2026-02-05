import streamlit as st
import pandas as pd
import pendulum
import os
import re
import json
from pendulum.tz import FixedTimezone

# --- SETUP ---
st.set_page_config(page_title="Last Standing Tactician", layout="wide", page_icon="🛡️")
DATA_FILE = "data/last_standing_schedule.csv"  # Legacy file (for backward compatibility)
ARMS_RACE_FILE = "data/arms_race_schedule.csv"
VS_DUEL_FILE = "data/vs_duel_schedule.csv"
SPECIAL_FILE = "data/special_events.csv"
DAILY_TEMPLATES_FILE = "data/daily_task_templates.csv"
ACTIVE_TASKS_FILE = "data/active_daily_tasks.csv"
RESTORE_TEMPLATES_FILE = "data/restore_daily_task_templates.csv"
SECRETARY_FILE         = "data/secretary_event.json"

if not os.path.exists("data"): os.makedirs("data")

# --- DATA HELPERS ---
def word_in_text(keyword, text):
    """Check if keyword appears as a whole word in text (case-insensitive)"""
    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
    return bool(re.search(pattern, text.lower()))

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
    if os.path.exists(SPECIAL_FILE): return pd.read_csv(SPECIAL_FILE, sep="\t")
    return pd.DataFrame(columns=["name", "days", "freq", "ref_week", "start_time", "end_time"])

def get_daily_templates():
    if os.path.exists(DAILY_TEMPLATES_FILE): return pd.read_csv(DAILY_TEMPLATES_FILE, sep="\t")
    return pd.DataFrame(columns=["name", "duration_n", "duration_r", "duration_sr", "duration_ssr", "duration_ur", "max_daily", "category", "color_code", "icon", "is_default"])

def get_active_tasks():
    if os.path.exists(ACTIVE_TASKS_FILE): return pd.read_csv(ACTIVE_TASKS_FILE, sep="\t")
    return pd.DataFrame(columns=["task_id", "task_name", "start_time_utc", "duration_minutes", "end_time_utc", "status"])

def cleanup_expired_tasks():
    if not os.path.exists(ACTIVE_TASKS_FILE): return
    active_df = pd.read_csv(ACTIVE_TASKS_FILE, sep="\t")
    if active_df.empty: return

    now_utc_str = pendulum.now('UTC')
    valid_tasks = []
    for _, task in active_df.iterrows():
        end_time = pendulum.parse(str(task['end_time_utc']))
        if end_time > now_utc_str:
            valid_tasks.append(task)

    if valid_tasks:
        pd.DataFrame(valid_tasks).to_csv(ACTIVE_TASKS_FILE, sep="\t", index=False)
    else:
        pd.DataFrame(columns=["task_id", "task_name", "start_time_utc", "duration_minutes", "end_time_utc", "status"]).to_csv(ACTIVE_TASKS_FILE, sep="\t", index=False)

def get_active_tasks_in_window(start_utc, end_utc):
    active_df = get_active_tasks()
    if active_df.empty: return []

    active_in_window = []
    for _, task in active_df.iterrows():
        task_start = pendulum.parse(str(task['start_time_utc']))
        task_end = pendulum.parse(str(task['end_time_utc']))

        # Check if task overlaps with window
        if task_start < end_utc and task_end > start_utc:
            active_in_window.append(str(task['task_name']))

    return active_in_window

def has_tasks_ending_in_window(start_utc, end_utc):
    """Check if any tasks end during this time window"""
    active_df = get_active_tasks()
    if active_df.empty: return False

    for _, task in active_df.iterrows():
        task_end = pendulum.parse(str(task['end_time_utc']))

        # Check if task ends within this window
        if start_utc <= task_end < end_utc:
            return True

    return False

def get_daily_activation_count(task_name, now_srv):
    """Count how many times a task was activated today (since last 02:00 server-time reset)"""
    active_df = get_active_tasks()
    if active_df.empty: return 0

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

        if base_name == task_name:
            task_start = pendulum.parse(str(task['start_time_utc']))
            if task_start >= daily_reset:
                count += 1

    return count

def is_event_in_window(event_row, window_start):
    """Check if a special event overlaps a 4-hour window.
    window_start: pendulum DateTime (server time).  Event times in the CSV are
    assumed to be in the same frame as window_start.
    """
    days = str(event_row['days']).split(',')
    if window_start.format('dddd') not in days: return False
    if event_row['freq'] == 'biweekly':
        if (window_start.week_of_year % 2) != (int(event_row['ref_week']) % 2): return False

    # Build absolute datetimes on the window's calendar date
    base   = window_start.start_of('day')
    sh, sm = map(int, str(event_row['start_time']).split(':'))
    eh, em = map(int, str(event_row['end_time']).split(':'))
    evt_start = base.set(hour=sh, minute=sm)
    evt_end   = base.set(hour=eh, minute=em)

    # end ≤ start means the event wraps past midnight → end is next day
    if evt_end <= evt_start:
        evt_end = evt_end.add(days=1)

    win_start = window_start
    win_end   = window_start.add(hours=4)

    # Standard interval-overlap check (works across midnight automatically)
    return evt_start < win_end and evt_end > win_start

# --- OVERLAP MAPPING FOR 2× DETECTION ---
OVERLAP_MAP = {
    "Base": ["Building Power", "Construction Speedup", "Building", "Construction"],
    "Tech": ["Tech Power", "Research Speedup", "Research"],
    "Hero": ["Hero Recruitment", "Hero EXP", "Hero Shard", "Hero", "Recruitment"],
    "Unit": ["Train T8 Unit", "Training Speedup", "Training", "Train", "Unit"],
    "Drone": ["Drone Data Point", "Drone Component", "Drone Part", "Stamina", "Drone"],
    "All-Rounder": ["Hero", "Building", "Research", "Train", "Construction", "Drone"]
}

def format_duration(total_minutes):
    """Format minutes into a compact string: '2d 4h', '1h 30m', '45m', or '0m'."""
    if total_minutes <= 0:
        return "0m"
    days  = int(total_minutes // 1440)
    hours = int((total_minutes % 1440) // 60)
    mins  = int(total_minutes % 60)
    if days:
        return f"{days}d {hours}h" if hours else f"{days}d"
    if hours:
        return f"{hours}h {mins}m" if mins else f"{hours}h"
    return f"{mins}m"

# --- SECRETARY BUFFS ---
SECRETARIES = {
    "Secretary of Strategy": {
        "icon": "🏥",
        "bonuses": [("Hospital Capacity", "+20%"), ("Unit Healing", "+20%")],
    },
    "Secretary of Defense": {
        "icon": "⚔️",
        "bonuses": [("Unit Training Cap", "+20%"), ("Training Speed", "+20%")],
    },
    "Secretary of Development": {
        "icon": "🏗️",
        "bonuses": [("Construction Speed", "+50%"), ("Research Speed", "+25%")],
    },
    "Secretary of Science": {
        "icon": "🔬",
        "bonuses": [("Research Speed", "+50%"), ("Construction Speed", "+25%")],
    },
    "Secretary of Interior": {
        "icon": "🏘️",
        "bonuses": [("Food", "+100%"), ("Iron", "+100%"), ("Coin", "+100%")],
    },
}

def get_secretary_event():
    """Return the active secretary event dict, or None."""
    if not os.path.exists(SECRETARY_FILE):
        return None
    with open(SECRETARY_FILE) as f:
        return json.load(f)

def save_secretary_event(event):
    """Persist (or clear) the active secretary event."""
    with open(SECRETARY_FILE, "w") as f:
        json.dump(event, f)

# --- TIME LOGIC ---
st.sidebar.title("🛡️ Command Center")
with st.sidebar:
    if st.session_state.get('nav_page', "Strategic Dashboard") != "Strategic Dashboard":
        if st.button("🏠 Dashboard", use_container_width=True, type="primary"):
            st.session_state['nav_page'] = "Strategic Dashboard"
            st.rerun()

    st.header("⚙️ Configuration")
    
    # 0. Server Timezone (default UTC-2; persists once changed)
    _srv_offsets = [f"UTC{'+' if h >= 0 else ''}{h}" for h in range(-12, 15)]
    _srv_sel = st.selectbox(
        "Server Timezone",
        _srv_offsets,
        index=_srv_offsets.index("UTC-2"),
        key="server_tz_select",
    )
    _srv_hours      = int(_srv_sel[3:])                # "UTC-2" → -2, "UTC+5" → 5
    server_tz       = FixedTimezone(_srv_hours * 3600)
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
    selected_tz = st.selectbox("Local Timezone", tz_options, index=0)

    if selected_tz == "Select Timezone (N/A)":
        user_tz       = server_tz
        user_tz_label = server_tz_label
        st.info(f"💡 Defaulting to {server_tz_label}. Select your zone for local times.")
    else:
        user_tz       = selected_tz
        user_tz_label = selected_tz

    # 2. Time Mode Selection (Fixes the time_mode error)
    time_mode = st.radio("Time Format", ["24h", "12h"], horizontal=True)
    fmt = "HH:mm" if time_mode == "24h" else "h:mm A"

now_utc    = pendulum.now('UTC')
now_server = pendulum.now(server_tz)          # game clock
now_local  = now_utc.in_timezone(user_tz)

# Game day resets at 02:00 server time
if now_server.hour < 2:
    vs_day = now_server.subtract(days=1).format('dddd')
    ar_day = now_server.subtract(days=1).format('dddd')
else:
    vs_day = now_server.format('dddd')
    ar_day = now_server.format('dddd')

# Current slot based on server time
# Slot boundaries: 02:00-06:00, 06:00-10:00, ..., 22:00-02:00 (server time)
current_slot = ((now_server.hour - 2) % 24 // 4) + 1

slot_start_hours = [2, 6, 10, 14, 18, 22]
start_hour = slot_start_hours[current_slot - 1]

# Start of the current 4-hour window in server time
if start_hour == 22:
    if now_server.hour >= 22:
        active_start = now_server.start_of('day').add(hours=22)
    else:  # hour 0 or 1 — still in previous day's Slot 6
        active_start = now_server.subtract(days=1).start_of('day').add(hours=22)
else:
    active_start = now_server.start_of('day').add(hours=start_hour)

# Game day always starts at 02:00 server time (used for full-day plan view)
if now_server.hour < 2:
    game_day_start = now_server.subtract(days=1).start_of('day').add(hours=2)
else:
    game_day_start = now_server.start_of('day').add(hours=2)

df = get_game_data()
specials_df = get_special_events()
cleanup_expired_tasks()
page = st.sidebar.selectbox("Navigate", ["Strategic Dashboard", "Weekly 2× Calendar", "Arms Race Scheduler", "VS Duel Manager", "Special Events Manager", "Secretary Buffs", "Daily Tasks Manager", "Speed-Up Calculator"], key="nav_page")

# ==========================================
# PAGE 1: STRATEGIC DASHBOARD
# ==========================================
if page == "Strategic Dashboard":
    # Debug toggle
    if 'show_debug' not in st.session_state:
        st.session_state.show_debug = False

    col_title, col_debug = st.columns([4, 1])
    with col_title:
        st.title(f"🛡️ {vs_day} Tactical Overview")
    with col_debug:
        if st.button("🐛 Debug" if not st.session_state.show_debug else "✅ Debug",
                     use_container_width=True,
                     type="secondary" if not st.session_state.show_debug else "primary"):
            st.session_state.show_debug = not st.session_state.show_debug
            st.rerun()

    # 1. Auto-reload the dashboard every 60 seconds so all times stay live
    st.html(
        '<script>setTimeout(function(){ location.reload(); }, 60000);</script>',
        unsafe_allow_javascript=True,
    )

    # 2. TIMERS (all relative to server time)
    reset_time = now_server.start_of('day').add(hours=2)
    if now_server.hour >= 2:
        reset_time = reset_time.add(days=1)
    diff_reset     = reset_time - now_server
    next_slot_time = active_start.add(hours=4)
    diff_slot      = next_slot_time - now_server

    # Secretary buff countdown (auto-clears on expiry)
    sec_event = get_secretary_event()
    sec_countdown = None
    if sec_event:
        sec_start = pendulum.parse(sec_event['start_time_utc'])
        sec_end   = pendulum.parse(sec_event['end_time_utc'])
        if now_utc >= sec_end:
            save_secretary_event(None)          # expired — clear once
        elif now_utc < sec_start:
            sec_countdown = {
                "label": f"🏛️ {sec_event['type'].replace('Secretary of ', '')} starts",
                "value": sec_start.in_timezone(user_tz).format(fmt),
            }
        else:                                   # buff is active right now
            sec_countdown = {
                "label": f"🏛️ {sec_event['type'].replace('Secretary of ', '')} ends",
                "value": sec_end.in_timezone(user_tz).format(fmt),
            }

    timer_cols = st.columns(5 if sec_countdown else 4)
    timer_cols[0].metric("📍 Local",          now_local.format(fmt))
    timer_cols[1].metric("🌍 Server",          now_server.format("HH:mm"))
    timer_cols[2].metric("🌙 VS Reset",       f"{diff_reset.hours}h {diff_reset.minutes}m")
    timer_cols[3].metric("📡 AR Slot Ends",   f"{diff_slot.hours}h {diff_slot.minutes}m")
    if sec_countdown:
        timer_cols[4].html(f"""
            <div style="background:#e8f5e9; border:2px solid #4caf50; border-radius:8px;
                        padding:10px; text-align:center;">
                <div style="color:#2e7d32; font-size:0.85em; font-weight:bold;">{sec_countdown['label']}</div>
                <div style="color:#1b5e20; font-size:1.3em; font-weight:bold;">{sec_countdown['value']}</div>
            </div>
        """)

    # 2. DATA FETCHING
    vs_active = df[(df['Day'] == vs_day) & (df['Type'] == 'VS')]
    ar_active = df[(df['Day'] == ar_day) & (df['Type'] == 'Arms Race') & (df['Slot'] == current_slot)]

    # 3. SCAN FOR BANNER UPDATES
    next_double = None
    next_drone = None

    for i in range(48):
        scan_t = active_start.add(hours=i*4)

        # Calculate game day (resets at 02:00 server time)
        if scan_t.hour < 2:
            s_day = scan_t.subtract(days=1).format('dddd')
        else:
            s_day = scan_t.format('dddd')

        # Calculate slot: Slot 1 is 02:00-06:00 UTC, Slot 2 is 06:00-10:00 UTC, etc.
        slot_n = ((scan_t.hour - 2) % 24 // 4) + 1

        b_ar = df[(df['Day'] == s_day) & (df['Type'] == 'Arms Race') & (df['Slot'] == slot_n)]
        b_vs = df[(df['Day'] == s_day) & (df['Type'] == 'VS')]

        if not b_ar.empty:
            ar_ev = b_ar['Event'].iloc[0]
            ar_root = ar_ev.split()[0]
            diff = scan_t - now_utc
            total_sec = max(0, diff.in_seconds())
            h, m = total_sec // 3600, (total_sec % 3600) // 60
            time_str = "NOW" if total_sec < 60 else f"in {int(h)}h {int(m)}m"

            if not next_double and not b_vs.empty:
                # Get all tasks for this slot for better keyword matching
                all_tasks = " ".join(b_ar['Task'].astype(str).tolist())
                ar_full_text = (str(ar_ev) + " " + all_tasks).lower()
                keywords = OVERLAP_MAP.get(ar_root, [ar_root.lower()])

                overlapping_skills = []
                for _, vs_row in b_vs.iterrows():
                    vs_event = str(vs_row['Event'])
                    vs_task = str(vs_row['Task'])

                    if any(word_in_text(kw, vs_event) or word_in_text(kw, vs_task) for kw in keywords) or \
                       (any(word_in_text(x, ar_full_text) for x in ["building", "construction"]) and
                        any(word_in_text(x, vs_event) or word_in_text(x, vs_task) for x in ["building", "construction"])):
                        overlapping_skills.append(str(vs_row['Event']))

                if overlapping_skills:
                    next_double = {"name": ar_ev, "skills": list(set(overlapping_skills)), "time": time_str}

            if not next_drone and "Drone" in ar_ev:
                next_drone = {"time": time_str}

        if next_double and next_drone: break

    # 5. THE STRATEGIC BANNER
    st.markdown(f"""
        <div style="background-color: #e3f2fd; border-left: 5px solid #1976d2; padding: 15px; border-radius: 4px; margin: 20px 0; display: flex; justify-content: space-between;">
            <div style="width: 48%;">
                <h4 style="color: #0d47a1; margin:0 0 5px 0;">⚡ STAMINA OPTIMIZATION</h4>
                <p style="color: #1565c0; margin:0; font-weight: 600;">Next Drone Boost: {next_drone['time'] if next_drone else 'N/A'}</p>
                <p style="color: #546e7a; margin:0; font-size: 0.8em;">Wait for this window to burn stamina packs.</p>
            </div>
            <div style="width: 2%; border-left: 1px solid #bbdefb;"></div>
            <div style="width: 48%;">
                <h4 style="color: #0d47a1; margin:0 0 5px 0;">🚀 NEXT DOUBLE VALUE: {next_double['name'] if next_double else 'N/A'}</h4>
                <p style="color: #1565c0; margin:0; font-weight: 600;">Skills: {" | ".join(next_double['skills']) if next_double else 'None'}</p>
                <p style="color: #1565c0; margin:0; font-weight: 500;">Starts {next_double['time'] if next_double else 'N/A'}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 6. ACTIVE TASKS
    st.subheader("⏳ Active Daily Tasks")
    active_df = get_active_tasks()
    if active_df.empty:
        st.info("No active tasks. Go to Daily Tasks Manager to activate tasks.")
    else:
        for idx, task in active_df.iterrows():
            now_utc_check = pendulum.now('UTC')
            start_time = pendulum.parse(str(task['start_time_utc']))
            end_time = pendulum.parse(str(task['end_time_utc']))

            # Calculate remaining time
            remaining = end_time - now_utc_check
            remaining_minutes = max(0, int(remaining.in_seconds() / 60))

            # Convert times to user timezone
            start_local = start_time.in_timezone(user_tz).format(fmt)
            end_local = end_time.in_timezone(user_tz).format(fmt)

            with st.container(border=True):
                cols = st.columns([3, 3, 2, 1])
                cols[0].write(f"**{task['task_name']}**")
                cols[1].write(f"🕐 {start_local} → {end_local}")
                cols[2].write(f"⏳ **{remaining_minutes}m** remaining")

                if cols[3].button("✅", key=f"complete_dash_{idx}"):
                    active_df = active_df[active_df['task_id'] != task['task_id']]
                    active_df.to_csv(ACTIVE_TASKS_FILE, sep="\t", index=False)
                    st.success(f"Task '{task['task_name']}' completed!")
                    st.rerun()

    st.divider()

    # 6.5 TASK TEMPLATES (Collapsible)
    with st.expander("📝 Task Templates", expanded=False):
        templates_df = get_daily_templates()

        if templates_df.empty:
            st.info("No task templates. Go to Daily Tasks Manager to create templates.")
        else:
            for idx, task in templates_df.iterrows():
                with st.container(border=True):
                    dur_n = int(task['duration_n'])
                    dur_r = int(task['duration_r'])
                    dur_sr = int(task['duration_sr'])
                    dur_ssr = int(task['duration_ssr'])
                    dur_ur = int(task['duration_ur'])
                    max_daily = int(task['max_daily'])

                    # Calculate daily activation count
                    activations_today = get_daily_activation_count(task['name'], now_server)
                    remaining = max_daily - activations_today
                    can_activate = remaining > 0

                    # Build list of available levels (duration > 0)
                    available_levels = []
                    if dur_n > 0: available_levels.append(('N', dur_n))
                    if dur_r > 0: available_levels.append(('R', dur_r))
                    if dur_sr > 0: available_levels.append(('SR', dur_sr))
                    if dur_ssr > 0: available_levels.append(('SSR', dur_ssr))
                    if dur_ur > 0: available_levels.append(('UR', dur_ur))

                    # Check if task has level variants
                    has_multiple_levels = len(available_levels) > 1

                    if has_multiple_levels:
                        cols = st.columns([2, 2, 2, 1])
                        cols[0].write(f"{task['icon']} **{task['name']}**")
                        cols[1].write(f"📂 {task['category']} | 📊 {remaining}/{max_daily} left")

                        # Create buttons for available levels only
                        num_levels = len(available_levels)
                        level_buttons = cols[2].columns(num_levels)

                        for btn_idx, (level_name, duration) in enumerate(available_levels):
                            if level_buttons[btn_idx].button(level_name, key=f"act_dash_{level_name}_{idx}", use_container_width=True, help=f"{duration}m", disabled=not can_activate):
                                now_utc_time = pendulum.now('UTC')
                                end_time = now_utc_time.add(minutes=duration)
                                task_id = f"{task['name']}_{now_utc_time.int_timestamp}"

                                new_active = pd.DataFrame([{
                                    'task_id': task_id,
                                    'task_name': f"{task['name']} ({level_name})",
                                    'start_time_utc': now_utc_time.to_iso8601_string(),
                                    'duration_minutes': duration,
                                    'end_time_utc': end_time.to_iso8601_string(),
                                    'status': 'active'
                                }])

                                active_df_new = get_active_tasks()
                                active_df_new = pd.concat([active_df_new, new_active], ignore_index=True)
                                active_df_new.to_csv(ACTIVE_TASKS_FILE, sep="\t", index=False)
                                st.success(f"✅ {task['name']} ({level_name}) activated!")
                                st.rerun()

                        if cols[3].button("🔗", key=f"goto_dash_{idx}", help="Go to Daily Tasks Manager"):
                            st.info("Navigate to Daily Tasks Manager page to edit templates")

                    elif len(available_levels) == 1:
                        # Single level - simple activation button
                        level_name, duration = available_levels[0]
                        cols = st.columns([2, 2, 1, 1])
                        cols[0].write(f"{task['icon']} **{task['name']}**")
                        cols[1].write(f"⏱️ {duration}m | 📂 {task['category']} | 📊 {remaining}/{max_daily} left")

                        if cols[2].button("▶️", key=f"act_dash_sl_{idx}", disabled=not can_activate):
                            now_utc_time = pendulum.now('UTC')
                            end_time = now_utc_time.add(minutes=duration)
                            task_id = f"{task['name']}_{now_utc_time.int_timestamp}"

                            new_active = pd.DataFrame([{
                                'task_id': task_id,
                                'task_name': task['name'],
                                'start_time_utc': now_utc_time.to_iso8601_string(),
                                'duration_minutes': duration,
                                'end_time_utc': end_time.to_iso8601_string(),
                                'status': 'active'
                            }])

                            active_df_new = get_active_tasks()
                            active_df_new = pd.concat([active_df_new, new_active], ignore_index=True)
                            active_df_new.to_csv(ACTIVE_TASKS_FILE, sep="\t", index=False)
                            st.success(f"✅ {task['name']} activated!")
                            st.rerun()

                        if cols[3].button("🔗", key=f"goto_dash_sl_{idx}", help="Go to Daily Tasks Manager"):
                            st.info("Navigate to Daily Tasks Manager page to edit templates")

                    else:
                        st.warning(f"No active durations configured for {task['name']}")

    st.divider()

    # 7. 24-HOUR OPTIMIZATION PLAN
    st.subheader("📅 24-Hour Optimization Plan")

    # Debug info to verify calculations
    if st.session_state.show_debug:
        st.subheader("🔧 Debug Info - Time Calculations")
        st.write("### Current Time Info")
        st.write(f"**Server Time ({server_tz_label}):** {now_server.format('YYYY-MM-DD HH:mm:ss ZZ')}")
        st.write(f"**UTC Time:** {now_utc.format('YYYY-MM-DD HH:mm:ss ZZ')}")
        st.write(f"**Local Time ({user_tz_label}):** {now_local.format('YYYY-MM-DD HH:mm:ss ZZ')}")
        st.write(f"**Server Hour:** {now_server.hour}")

        st.write("### Slot Calculation Step-by-Step (Using Server Time)")
        st.write("**Slot boundaries (server):** Slot1=02-06, Slot2=06-10, Slot3=10-14, Slot4=14-18, Slot5=18-22, Slot6=22-02")
        calc_step1 = now_server.hour - 2
        calc_step2 = calc_step1 % 24
        calc_step3 = calc_step2 // 4
        calc_step4 = calc_step3 + 1
        st.write(f"**Formula:** ((server_hour - 2) % 24 // 4) + 1")
        st.write(f"**Step 1:** {now_server.hour} - 2 = {calc_step1}")
        st.write(f"**Step 2:** {calc_step1} % 24 = {calc_step2}")
        st.write(f"**Step 3:** {calc_step2} // 4 = {calc_step3}")
        st.write(f"**Step 4:** {calc_step3} + 1 = {calc_step4}")
        st.write(f"**Result: Slot {calc_step4} (global, same for all players)**")

        # Show what this means in local time
        slot_starts = [2, 6, 10, 14, 18, 22]
        current_slot_start_srv = slot_starts[calc_step4 - 1]
        current_slot_start_local = now_server.start_of('day').add(hours=current_slot_start_srv).in_timezone(user_tz)
        st.write(f"**In your timezone:** Slot {calc_step4} is {current_slot_start_local.format('HH:mm')}-{current_slot_start_local.add(hours=4).format('HH:mm')} local")

        st.write("### Calculated Slot Info")
        st.write(f"**Current Slot (calculated):** {current_slot}")
        st.write(f"**Current Game Day (calculated):** {ar_day}")
        st.write(f"**Active Window Start (Local):** {active_start.in_timezone(user_tz).format('YYYY-MM-DD HH:mm:ss')}")
        st.write(f"**Active Window End (Local):** {active_start.add(hours=4).in_timezone(user_tz).format('YYYY-MM-DD HH:mm:ss')}")

        st.write("### First Row of Optimization Table (Should be current slot)")
        first_row_srv   = active_start
        first_row_local = first_row_srv.in_timezone(user_tz)
        # Game day resets at 02:00 server time
        if first_row_srv.hour < 2:
            first_row_day = first_row_srv.subtract(days=1).format('dddd')
        else:
            first_row_day = first_row_srv.format('dddd')
        first_row_slot = ((first_row_srv.hour - 2) % 24 // 4) + 1

        st.write(f"**First Row Time (Server):** {first_row_srv.format('HH:mm')}")
        st.write(f"**First Row Time (Local):** {first_row_local.format('HH:mm')}")
        st.write(f"**First Row Day:** {first_row_day}")
        st.write(f"**First Row Slot:** {first_row_slot}")

        first_row_ar = df[(df['Day'] == first_row_day) & (df['Type'] == 'Arms Race') & (df['Slot'] == first_row_slot)]
        if not first_row_ar.empty:
            st.write(f"**First Row Arms Race:** {first_row_ar['Event'].iloc[0]}")
            if first_row_slot == current_slot:
                st.success(f"✅ MATCH! First row correctly shows Slot {current_slot}")
        else:
            st.warning(f"⚠️ No Arms Race found for {first_row_day} Slot {first_row_slot}")

        if first_row_slot != current_slot:
            st.error(f"⚠️ SLOT MISMATCH: First row is Slot {first_row_slot}, but current slot is {current_slot}!")

        st.write("### 2× Detection Debug (First Row)")
        if first_row_ar.empty:
            st.write("No Arms Race found for first row")
        else:
            st.write(f"**Arms Race Event:** {first_row_ar['Event'].iloc[0]}")
            st.write(f"**Arms Race Task:** {first_row_ar['Task'].iloc[0] if 'Task' in first_row_ar.columns else 'N/A'}")

            first_row_vs = df[(df['Day'] == first_row_day) & (df['Type'] == 'VS')]
            if first_row_vs.empty:
                st.write(f"**VS Events:** None found for {first_row_day}")
                st.info("ℹ️ No 2× possible - no VS event on this day")
            else:
                st.write(f"**VS Event:** {first_row_vs.iloc[0]['Event'] if not first_row_vs.empty else 'N/A'}")
                st.write(f"**VS Tasks:** {list(first_row_vs['Task'])}")

                # Check overlap
                ar_event = first_row_ar['Event'].iloc[0]
                ar_root = ar_event.split()[0]
                keywords = OVERLAP_MAP.get(ar_root, [ar_root.lower()])
                st.write(f"**Looking for keywords:** {keywords}")

                found_match = False
                for _, vs_row in first_row_vs.iterrows():
                    vs_event = str(vs_row['Event'])
                    vs_task = str(vs_row['Task'])

                    # Check both Event and Task (whole word matching)
                    matching_kw_event = [kw for kw in keywords if word_in_text(kw, vs_event)]
                    matching_kw_task = [kw for kw in keywords if word_in_text(kw, vs_task)]

                    if matching_kw_event:
                        st.success(f"✅ MATCH found! VS Event '{vs_row['Event']}' contains keyword(s): {matching_kw_event}")
                        found_match = True
                        break
                    elif matching_kw_task:
                        st.success(f"✅ MATCH found! VS Task '{vs_row['Task']}' contains keyword(s): {matching_kw_task}")
                        found_match = True
                        break

                if not found_match:
                    st.warning(f"⚠️ No keyword match found in VS Event or Task. Check if OVERLAP_MAP for '{ar_root}' needs updating.")

        st.write("### What the App Found")
        current_ar = df[(df['Day'] == ar_day) & (df['Type'] == 'Arms Race') & (df['Slot'] == current_slot)]
        if not current_ar.empty:
            st.write(f"**Found in CSV:** {current_ar['Event'].iloc[0]}")
            st.success(f"✅ Match found: {current_ar['Event'].iloc[0]}")
        else:
            st.error(f"❌ NOT FOUND in CSV for Day='{ar_day}', Slot={current_slot}")

            st.write("### All Arms Race entries in CSV:")
            all_ar = df[df['Type'] == 'Arms Race'].sort_values(['Day', 'Slot'])
            st.dataframe(all_ar[['Day', 'Slot', 'Event']], hide_index=True)

            st.write("### Possible Reasons for Mismatch:")
            st.write(f"1. **Wrong Day?** Looking for '{ar_day}' but Hero Development might be saved for a different day")
            st.write(f"2. **Wrong Slot?** Looking for Slot {current_slot} but Hero Development might be in a different slot")
            st.write(f"3. **Not Saved?** Hero Development might not be saved in the CSV file yet")
            st.write(f"4. **Check:** Find Hero Development in the table above and compare the Day and Slot")

    st.caption(f"📌 Server: {now_server.format('ddd HH:mm')} ({server_tz_label}) · Slot {current_slot} · {ar_day}  |  💡 Hover over cells for full content")
    plan_data = []
    for i in range(6):
        b_srv   = active_start.add(hours=i*4)
        b_local = b_srv.in_timezone(user_tz)

        # Calculate game day (resets at 02:00 server time)
        if b_srv.hour < 2:
            b_game_day = b_srv.subtract(days=1).format('dddd')
        else:
            b_game_day = b_srv.format('dddd')

        # Slot from server-time hour
        b_slot_n = ((b_srv.hour - 2) % 24 // 4) + 1

        b_ar = df[(df['Day'] == b_game_day) & (df['Type'] == 'Arms Race') & (df['Slot'] == b_slot_n)]
        b_vs = df[(df['Day'] == b_game_day) & (df['Type'] == 'VS')]
        ev_name = b_ar['Event'].iloc[0] if not b_ar.empty else "N/A"

        # Get all tasks for this slot (there may be multiple rows per slot now)
        all_ar_tasks = " ".join(b_ar['Task'].astype(str).tolist()) if not b_ar.empty else ""

        active_specials = [s_row['name'] for _, s_row in specials_df.iterrows() if is_event_in_window(s_row, b_srv)]
        specials_str = ", ".join(active_specials) if active_specials else ""

        # Get active daily tasks in this window
        window_end = b_srv.add(hours=4)
        active_daily_tasks = get_active_tasks_in_window(b_srv, window_end)
        daily_tasks_str = ", ".join(active_daily_tasks) if active_daily_tasks else ""

        # Check if any tasks are ending in this window
        tasks_ending = has_tasks_ending_in_window(b_srv, window_end)

        status = "1×"
        match_debug = []
        if not b_ar.empty and not b_vs.empty:
            ar_root = ev_name.split()[0]
            # Include all tasks for this slot in the matching text
            ar_full_text = (str(ev_name) + " " + all_ar_tasks).lower()
            keywords = OVERLAP_MAP.get(ar_root, [ar_root.lower()])

            # Check both VS Event name and Task for keyword matches
            for _, vs_row in b_vs.iterrows():
                vs_event = str(vs_row['Event']).lower()
                vs_task = str(vs_row['Task']).lower()

                # Debug: track what we're checking
                match_debug.append({
                    'ar_root': ar_root,
                    'keywords': keywords,
                    'vs_event': vs_event,
                    'vs_task': vs_task,
                    'i': i
                })

                # Check if keywords match in either VS Event or Task (whole word matching)
                if any(word_in_text(kw, vs_event) or word_in_text(kw, vs_task) for kw in keywords) or \
                   (any(word_in_text(x, ar_full_text) for x in ["building", "construction"]) and \
                    any(word_in_text(x, vs_event) or word_in_text(x, vs_task) for x in ["building", "construction"])):
                    status = "⭐ 2×"
                    break

        is_current = (b_srv <= now_server < b_srv.add(hours=4))

        plan_data.append({
            "Day": b_local.format('dddd'), "Time": f"{b_local.format(fmt)}–{b_local.add(hours=4).format(fmt)}",
            "Arms Race": ev_name, "Special Events": specials_str, "Daily Tasks": daily_tasks_str,
            "Optimization": status, "Tasks Ending": tasks_ending,
            "is_current": is_current,
            "match_debug": match_debug
        })

    plan_df = pd.DataFrame(plan_data)

    # Debug: Show what's in the plan
    if st.session_state.show_debug:
        st.subheader("🐛 2× Detection Debug")
        st.write(f"**Total rows:** {len(plan_df)}")
        st.write(f"**Rows with 2×:** {len(plan_df[plan_df['Optimization'] == '⭐ 2×'])}")
        st.write(f"**Rows with Tasks Ending:** {len(plan_df[plan_df['Tasks Ending'] == True])}")
        st.write(f"**Rows with Both:** {len(plan_df[(plan_df['Optimization'] == '⭐ 2×') & (plan_df['Tasks Ending'] == True)])}")

        for idx, row in plan_df.iterrows():
            b_srv = active_start.add(hours=idx*4)
            if b_srv.hour < 2:
                b_game_day = b_srv.subtract(days=1).format('dddd')
            else:
                b_game_day = b_srv.format('dddd')

            b_slot_n = ((b_srv.hour - 2) % 24 // 4) + 1
            b_ar = df[(df['Day'] == b_game_day) & (df['Type'] == 'Arms Race') & (df['Slot'] == b_slot_n)]
            b_vs = df[(df['Day'] == b_game_day) & (df['Type'] == 'VS')]

            vs_info = "None" if b_vs.empty else f"{b_vs.iloc[0]['Event']} - {b_vs.iloc[0]['Task']}"

            # Show row info with highlighting indicators
            status_icon = "⭐" if row['Optimization'] == "⭐ 2×" else "○"
            tasks_icon = "📋" if row.get('Tasks Ending', False) else "○"
            st.write(f"**Row {idx} ({row['Time']}):** {row['Arms Race']}")
            st.write(f"  Game Day: {b_game_day} Slot {b_slot_n} | VS: {vs_info}")
            st.write(f"  Status: {status_icon} {row['Optimization']} | Tasks Ending: {tasks_icon} {row.get('Tasks Ending', False)}")

            # Show detailed matching info
            if 'match_debug' in row and row['match_debug']:
                for md in row['match_debug']:
                    st.write(f"  → Checking: ar_root={md['ar_root']}, keywords={md['keywords']}")
                    st.write(f"     vs_event='{md['vs_event']}', vs_task='{md['vs_task']}'")
                    # Check which keywords match
                    matches = [kw for kw in md['keywords'] if kw.lower() in md['vs_event'] or kw.lower() in md['vs_task']]
                    if matches:
                        st.success(f"     ✓ Matched keywords: {matches}")
                    else:
                        st.error(f"     ✗ No keyword matches")

    def highlight_optimization(row):
        # Blue highlight for tasks ending (takes priority)
        if row['Tasks Ending']:
            return ['background-color: #1565c0; color: #ffffff; font-weight: bold'] * 6
        # Green highlight for double value
        elif row['Optimization'] == "Double Value":
            return ['background-color: #1b5e20; color: #ffffff; font-weight: bold'] * 6
        return [''] * 6

    # Create display dataframe without the "Tasks Ending" column
    display_df = plan_df[["Day", "Time", "Arms Race", "Special Events", "Daily Tasks", "Optimization"]].copy()

    # Apply styling using the full dataframe for logic but style the display dataframe
    def highlight_row(idx):
        row = plan_df.iloc[idx]
        if row['Tasks Ending']:
            return ['background-color: #1565c0; color: #ffffff; font-weight: bold'] * 6
        elif row['Optimization'] == "⭐ 2×":
            return ['background-color: #1b5e20; color: #ffffff; font-weight: bold'] * 6
        return [''] * 6

    styled_df = display_df.style.apply(lambda row: highlight_row(row.name), axis=1)

    # Display custom table with Details button in last column
    # Header row - must match table row structure
    header_content_col, header_btn_col = st.columns([95, 5])

    with header_content_col:
        header_html = """
        <div style="padding: 8px 5px; margin: 2px 0; display: flex; align-items: center; gap: 5px; font-weight: bold;">
            <div style="width: 70px; flex-shrink: 0;">Day</div>
            <div style="width: 100px; flex-shrink: 0;">Time</div>
            <div style="width: 120px; flex-shrink: 0;">Arms Race</div>
            <div style="flex: 1; min-width: 100px;">Special Events</div>
            <div style="flex: 1; min-width: 100px;">Daily Tasks</div>
            <div style="width: 50px; flex-shrink: 0;">Value</div>
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)

    with header_btn_col:
        st.markdown("**Details**")

    st.divider()

    # Data rows with highlighting
    for idx, (_, row_data) in enumerate(display_df.iterrows()):
        full_row = plan_df.iloc[idx]

        # Determine background color (priority: both > tasks ending > 2×)
        bg_color = ""
        text_color = "white"
        if full_row['Tasks Ending'] and row_data['Optimization'] == "⭐ 2×":
            bg_color = "#DAA520"  # Gold for both tasks ending AND double value
            text_color = "black"
        elif full_row['Tasks Ending']:
            bg_color = "#1565c0"  # Blue for tasks ending
        elif row_data['Optimization'] == "⭐ 2×":
            bg_color = "#1b5e20"  # Green for double value

        # Debug: Log what we're doing (only show in console, not to user)
        if bg_color:  # Only log when we're applying color
            import sys
            print(f"Row {idx}: Applying color {bg_color} - Optimization={row_data['Optimization']}, Tasks Ending={full_row['Tasks Ending']}", file=sys.stderr)

        # Get content, hide empty Special Events and Daily Tasks
        special_events_content = row_data['Special Events'] if row_data['Special Events'] else ""
        daily_tasks_content = row_data['Daily Tasks'] if row_data['Daily Tasks'] else ""

        # Use HTML flexbox for all rows to ensure consistent alignment
        is_current = full_row.get('is_current', False)
        now_badge = '<span style="background:#e53935; color:white; font-size:0.7em; font-weight:bold; padding:1px 4px; border-radius:3px; margin-left:2px;">◀ NOW</span>' if is_current else ''
        border_left = "border-left: 3px solid #e53935;" if is_current else ""
        row_style = f"background-color: {bg_color}; color: {text_color}; {border_left}" if bg_color else f"background-color: transparent; color: inherit; {border_left}"

        # Put the row content and button on the same line
        content_col, btn_col = st.columns([95, 5])

        with content_col:
            row_html = f"""
            <div style="{row_style} padding: 8px 5px; margin: 2px 0; border-radius: 4px; display: flex; align-items: center; gap: 5px;">
                <div style="width: 70px; flex-shrink: 0; font-size: 0.9em;">{row_data["Day"]}</div>
                <div style="width: 100px; flex-shrink: 0; font-size: 0.9em;">{row_data["Time"]}{now_badge}</div>
                <div style="width: 120px; flex-shrink: 0; font-size: 0.9em;">{row_data["Arms Race"]}</div>
                <div style="flex: 1; min-width: 100px; font-size: 0.85em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{special_events_content}</div>
                <div style="flex: 1; min-width: 100px; font-size: 0.85em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{daily_tasks_content}</div>
                <div style="width: 50px; flex-shrink: 0; font-size: 0.9em;">{row_data["Optimization"]}</div>
            </div>
            """
            st.markdown(row_html, unsafe_allow_html=True)

        with btn_col:
            if st.button("📋", key=f"detail_row_{idx}", help="View full details"):
                if st.session_state.get('selected_detail_row') == idx:
                    st.session_state.selected_detail_row = None
                else:
                    st.session_state.selected_detail_row = idx

    # Show detailed view if a row button was clicked
    if 'selected_detail_row' in st.session_state and st.session_state.selected_detail_row is not None:
        idx = st.session_state.selected_detail_row
        row = display_df.iloc[idx]
        full_row = plan_df.iloc[idx]

        with st.container(border=True):
            st.subheader(f"📊 {row['Day']} {row['Time']}")

            col1, col2 = st.columns([1, 2])

            with col1:
                st.write(f"**📅 Day:** {row['Day']}")
                st.write(f"**🕐 Time:** {row['Time']}")
                st.write(f"**⚔️ Arms Race:** {row['Arms Race']}")
                st.write(f"**💎 Value:** {row['Optimization']}")

                if full_row['Tasks Ending']:
                    st.info("🔵 **Status:** Tasks Ending in This Window")
                elif row['Optimization'] == "⭐ 2×":
                    st.success("🟢 **Status:** Double Value Active")
                else:
                    st.write("**Status:** Regular")

            with col2:
                st.write("**🎯 Special Events:**")
                if row['Special Events']:
                    events = [e.strip() for e in row['Special Events'].split(',')]
                    for event in events:
                        st.write(f"• {event}")
                else:
                    st.write("_(none)_")

                st.write("")
                st.write("**📋 Daily Tasks:**")
                if row['Daily Tasks']:
                    tasks = [t.strip() for t in row['Daily Tasks'].split(',')]
                    for task in tasks:
                        st.write(f"• {task}")
                else:
                    st.write("_(none)_")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**🔥 Current Arms Race: {ar_active['Event'].iloc[0] if not ar_active.empty else 'N/A'}**")
        st.dataframe(ar_active[['Task', 'Points']], hide_index=True, use_container_width=True)
    with c2:
        st.write(f"**🎯 Current VS Duel: {vs_day}**")
        st.dataframe(vs_active[['Task', 'Points']], hide_index=True, use_container_width=True)

# ==========================================
# PAGE 2: WEEKLY 2× CALENDAR
# ==========================================
elif page == "Weekly 2× Calendar":
    st.title("📅 Weekly 2× Opportunities Calendar")
    st.caption("Plan your week: See when to use resources for points and when to save for upcoming events")

    # Resource mapping by event type (what to use/save)
    RESOURCE_MAP = {
        "Radar Training": "Radar tasks, Stamina, Drone parts",
        "Total Mobilization": "Speedups, Training resources, Tech/Building power",
        "Enemy Buster": "Trade trucks, Secret tasks, Speedups",
        "Train Heroes": "Hero shards (UR/SR), Skill medals, Weapon shards",
        "Base Expansion": "Building speedups, Trade trucks, Survivors",
        "Age of Science": "Tech speedups, Valor badges, Drone components"
    }

    # Get VS events for the week
    df = get_game_data()
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # Calculate which day is today in game terms (resets at 02:00 server time)
    if now_server.hour < 2:
        today_game_day = now_server.subtract(days=1).format('dddd')
    else:
        today_game_day = now_server.format('dddd')

    # Display calendar
    for day_idx, day in enumerate(days_order):
        # Get VS event for this day
        vs_events = df[(df['Day'] == day) & (df['Type'] == 'VS')]

        if vs_events.empty:
            vs_event_name = "Rest Day"
            vs_tasks = []
        else:
            vs_event_name = vs_events.iloc[0]['Event']
            vs_tasks = vs_events['Task'].tolist()

        # Determine if this is today, past, or future
        is_today = (day == today_game_day)

        # Calculate days until this day
        days_until = (day_idx - days_order.index(today_game_day)) % 7

        # Get all Arms Race events for this day and find 2× matches
        ar_events = df[(df['Day'] == day) & (df['Type'] == 'Arms Race')]

        double_value_events = []
        if not vs_events.empty and not ar_events.empty:
            # Group AR events by slot
            for slot in range(1, 7):
                slot_ar = ar_events[ar_events['Slot'] == slot]
                if not slot_ar.empty:
                    ar_event_name = slot_ar.iloc[0]['Event']
                    ar_root = ar_event_name.split()[0]

                    # Get all tasks for this slot
                    all_ar_tasks = " ".join(slot_ar['Task'].astype(str).tolist())
                    ar_full_text = (str(ar_event_name) + " " + all_ar_tasks).lower()
                    keywords = OVERLAP_MAP.get(ar_root, [ar_root.lower()])

                    # Check if this AR event gets 2× from VS event
                    for _, vs_row in vs_events.iterrows():
                        vs_event = str(vs_row['Event'])
                        vs_task = str(vs_row['Task'])

                        if any(word_in_text(kw, vs_event) or word_in_text(kw, vs_task) for kw in keywords) or \
                           (any(word_in_text(x, ar_full_text) for x in ["building", "construction"]) and \
                            any(word_in_text(x, vs_event) or word_in_text(x, vs_task) for x in ["building", "construction"])):
                            # Calculate local time for this slot
                            slot_start_srv = now_server.start_of('day').add(hours=(slot-1)*4+2)
                            slot_start_local = slot_start_srv.in_timezone(user_tz).format(fmt)
                            double_value_events.append(f"Slot {slot} ({slot_start_local}): {ar_event_name}")
                            break

        # Determine card color based on day status
        if is_today:
            border_color = "#1976d2"  # Blue for today
            bg_color = "#e3f2fd"
            status_badge = "🔵 TODAY"
        elif days_until == 1:
            border_color = "#388e3c"  # Green for tomorrow
            bg_color = "#e8f5e9"
            status_badge = "🟢 TOMORROW"
        elif days_until <= 3:
            border_color = "#f57c00"  # Orange for soon
            bg_color = "#fff3e0"
            status_badge = f"🟠 IN {days_until} DAYS"
        else:
            border_color = "#757575"  # Gray for later
            bg_color = "#f5f5f5"
            status_badge = f"⚪ IN {days_until} DAYS"

        # Display day card
        with st.container(border=True):
            # Header with day name and status
            header_html = f"""
            <div style="background: linear-gradient(90deg, {border_color}, {border_color}22);
                        padding: 10px 15px; margin: -10px -10px 15px -10px; border-radius: 4px 4px 0 0;
                        border-bottom: 2px solid {border_color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #1a1a1a;">📅 {day}</h3>
                    <span style="background-color: white; padding: 4px 12px; border-radius: 12px;
                                 font-weight: bold; font-size: 0.85em; color: {border_color};">{status_badge}</span>
                </div>
            </div>
            """
            st.markdown(header_html, unsafe_allow_html=True)

            # VS Event section
            col1, col2 = st.columns([1, 2])

            with col1:
                st.write("### ⚔️ VS Event")
                st.write(f"**{vs_event_name}**")

                # Generate dynamic resource tip
                if vs_event_name == "Rest Day":
                    tip = "💡 No VS event today - Focus on daily tasks and stockpiling"
                    tip_color = "#9e9e9e"
                elif vs_event_name in RESOURCE_MAP:
                    resources = RESOURCE_MAP[vs_event_name]
                    # This is a VS event day - USE resources to get points
                    tip = f"✅ USE TODAY: {resources}"
                    tip_color = "#4caf50"  # Green for USE
                else:
                    tip = "💡 Plan your resources"
                    tip_color = "#9e9e9e"

                st.markdown(f"""
                <div style="background-color: {tip_color}22; border-left: 3px solid {tip_color};
                            padding: 8px 12px; margin-top: 10px; border-radius: 4px;">
                    <small>{tip}</small>
                </div>
                """, unsafe_allow_html=True)

                # Show what to save for upcoming events (next 2-3 days)
                upcoming_tips = []
                for look_ahead in range(1, 4):  # Look 1-3 days ahead
                    check_idx = (day_idx + look_ahead) % 7
                    check_day = days_order[check_idx]
                    check_events = df[(df['Day'] == check_day) & (df['Type'] == 'VS')]
                    if not check_events.empty:
                        check_event_name = check_events.iloc[0]['Event']
                        if check_event_name != "Rest Day" and check_event_name in RESOURCE_MAP:
                            resources = RESOURCE_MAP[check_event_name]
                            days_label = "Tomorrow" if look_ahead == 1 else check_day
                            upcoming_tips.append(f"🔹 {days_label}: {resources}")

                if upcoming_tips:
                    st.markdown("**💾 Save for Upcoming:**")
                    for tip_line in upcoming_tips[:2]:  # Show max 2
                        st.markdown(f"<small>{tip_line}</small>", unsafe_allow_html=True)

            with col2:
                st.write("### ⭐ 2× Opportunities")
                if double_value_events:
                    for dv_event in double_value_events:
                        st.markdown(f"""
                        <div style="background-color: #1b5e2022; border-left: 3px solid #1b5e20;
                                    padding: 6px 10px; margin: 4px 0; border-radius: 4px;">
                            <span style="color: #1b5e20; font-weight: bold;">⭐</span> {dv_event}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No 2× opportunities detected for this day")

        st.divider()

    # Summary stats at bottom
    st.subheader("📊 Weekly Summary")

    total_2x_opportunities = 0
    days_with_2x = []

    for day in days_order:
        vs_events = df[(df['Day'] == day) & (df['Type'] == 'VS')]
        ar_events = df[(df['Day'] == day) & (df['Type'] == 'Arms Race')]

        has_2x = False
        if not vs_events.empty and not ar_events.empty:
            for slot in range(1, 7):
                slot_ar = ar_events[ar_events['Slot'] == slot]
                if not slot_ar.empty:
                    ar_event_name = slot_ar.iloc[0]['Event']
                    ar_root = ar_event_name.split()[0]
                    all_ar_tasks = " ".join(slot_ar['Task'].astype(str).tolist())
                    ar_full_text = (str(ar_event_name) + " " + all_ar_tasks).lower()
                    keywords = OVERLAP_MAP.get(ar_root, [ar_root.lower()])

                    for _, vs_row in vs_events.iterrows():
                        vs_event = str(vs_row['Event'])
                        vs_task = str(vs_row['Task'])

                        if any(word_in_text(kw, vs_event) or word_in_text(kw, vs_task) for kw in keywords) or \
                           (any(word_in_text(x, ar_full_text) for x in ["building", "construction"]) and \
                            any(word_in_text(x, vs_event) or word_in_text(x, vs_task) for x in ["building", "construction"])):
                            total_2x_opportunities += 1
                            has_2x = True

        if has_2x:
            days_with_2x.append(day)

    col1, col2, col3 = st.columns(3)
    col1.metric("🎯 Total 2× Opportunities This Week", total_2x_opportunities)
    col2.metric("📅 Days with 2× Bonuses", len(days_with_2x))
    col3.metric("💎 Best Days", ", ".join(days_with_2x[:3]) if days_with_2x else "None")

# ==========================================
# PAGE 3: ARMS RACE SCHEDULER
# ==========================================
elif page == "Arms Race Scheduler":
    st.title("🔄 Arms Race Scheduler")
    categories = ["Base Building", "Tech Research", "Drone Boost", "Hero Development", "Unit Progression", "All-Rounder"]
    target_day = st.selectbox("Select Day to Manage", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    df = get_game_data()

    with st.form("ar_scheduler_form"):
        st.write(f"### Edit Rotation: {target_day}")
        day_map = {i: categories[0] for i in range(1, 7)}
        if not df.empty:
            existing = df[(df['Day'] == target_day) & (df['Type'] == 'Arms Race')]
            for _, row in existing.iterrows():
                day_map[int(row['Slot'])] = row['Event']

        cols = st.columns(3)
        selections = []
        for i in range(1, 7):
            # Slot time range in server time, displayed in local tz
            slot_start_srv = now_server.start_of('day').add(hours=(i-1)*4+2)
            slot_end_srv   = slot_start_srv.add(hours=4)
            slot_start_local = slot_start_srv.in_timezone(user_tz).format('HH:mm:ss')
            slot_end_local   = slot_end_srv.in_timezone(user_tz).format('HH:mm:ss')

            idx = categories.index(day_map[i]) if day_map[i] in categories else 0
            # Use target_day in key to force update when day changes
            sel = cols[(i-1)%3].selectbox(f"Slot {i} ({slot_start_local}-{slot_end_local})", categories, index=idx, key=f"s_in_{target_day}_{i}")
            selections.append(sel)

        if st.form_submit_button("💾 Save"):
            try:
                # Load only Arms Race data (not VS data - that's in a separate file)
                if os.path.exists(ARMS_RACE_FILE):
                    arms_race_df = pd.read_csv(ARMS_RACE_FILE, sep="\t")
                else:
                    arms_race_df = pd.DataFrame(columns=["Day", "Event", "Task", "Points", "Slot"])

                # Remove existing entries for this day
                arms_race_df = arms_race_df[arms_race_df['Day'] != target_day]

                # Add new entries
                new_rows = []
                for i, event_name in enumerate(selections, start=1):
                    new_rows.append({
                        "Day": target_day,
                        "Event": event_name,
                        "Task": event_name,
                        "Points": "Standard",
                        "Slot": i
                    })

                new_df = pd.DataFrame(new_rows)
                arms_race_df = pd.concat([arms_race_df, new_df], ignore_index=True)

                # Sort by Day and Slot for consistency
                arms_race_df = arms_race_df.sort_values(['Day', 'Slot'])

                # Save to Arms Race CSV (VS data remains separate and unchanged)
                arms_race_df.to_csv(ARMS_RACE_FILE, sep="\t", index=False, encoding='utf-8')

                # Verify the save by reading back
                verify_df = pd.read_csv(ARMS_RACE_FILE, sep="\t")
                verify_entries = verify_df[verify_df['Day'] == target_day]

                st.success(f"✅ Schedule for {target_day} saved successfully! ({len(verify_entries)} slots saved)")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error saving schedule: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

    st.divider()
    st.subheader(f"📍 Confirmed {target_day} Schedule")
    final_view_df = get_game_data()
    view_df = final_view_df[(final_view_df['Day'] == target_day) & (final_view_df['Type'] == 'Arms Race')].copy()
    if not view_df.empty:
        view_df = view_df.sort_values('Slot').drop_duplicates(subset=['Slot'])
        # Slot 1 starts at 02:00 server time
        view_df['Time'] = view_df.apply(lambda r: now_server.start_of('day').add(hours=(int(r['Slot'])-1)*4+2).in_timezone(user_tz).format(fmt), axis=1)
        st.dataframe(view_df[['Time', 'Event']], hide_index=True, use_container_width=True)
    else:
        st.info("No entries found.")

    st.divider()
    st.subheader("🔧 Bulk Edit Tasks")

    with st.expander("Find and Replace Tasks/Points", expanded=False):
        # Load current arms race data
        if os.path.exists(ARMS_RACE_FILE):
            arms_df = pd.read_csv(ARMS_RACE_FILE, sep="\t")

            # Get unique event names
            unique_events = sorted(arms_df['Event'].unique().tolist())

            col1, col2 = st.columns(2)
            with col1:
                st.write("### Find")
                find_event = st.selectbox("Select Event to Modify", unique_events, key="find_event")

                # Show current occurrences with tasks
                matching_rows = arms_df[arms_df['Event'] == find_event]
                st.write(f"**Found {len(matching_rows)} task(s) across {len(matching_rows.groupby(['Day', 'Slot']))} slot(s):**")

                # Display with all details
                display_df = matching_rows[['Day', 'Slot', 'Task', 'Points']].copy()
                display_df = display_df.sort_values(['Day', 'Slot'])
                st.dataframe(display_df, hide_index=True, use_container_width=True)

            with col2:
                st.write("### Replace With")
                new_event_name = st.text_input("New Event Name (leave blank to keep)", value="", key="new_event")
                new_task_name = st.text_input("New Task Name (leave blank to keep)", value="", key="new_task")
                new_points = st.text_input("New Points (leave blank to keep)", value="", key="new_points")

                st.write("### Apply To")
                apply_scope = st.radio(
                    "Scope",
                    ["All occurrences", "Specific day only"],
                    key="apply_scope"
                )

                if apply_scope == "Specific day only":
                    days_with_event = sorted(matching_rows['Day'].unique().tolist())
                    specific_day = st.selectbox("Select Day", days_with_event, key="specific_day")

            if st.button("🔄 Apply Changes", type="primary", use_container_width=True):
                changes_made = False

                # Create a copy to modify
                updated_df = arms_df.copy()

                # Determine which rows to update
                if apply_scope == "All occurrences":
                    mask = updated_df['Event'] == find_event
                else:
                    mask = (updated_df['Event'] == find_event) & (updated_df['Day'] == specific_day)

                # Apply changes
                if new_event_name:
                    updated_df.loc[mask, 'Event'] = new_event_name
                    changes_made = True

                if new_task_name:
                    updated_df.loc[mask, 'Task'] = new_task_name
                    changes_made = True

                if new_points:
                    updated_df.loc[mask, 'Points'] = new_points
                    changes_made = True

                if changes_made:
                    # Save back to file
                    updated_df.to_csv(ARMS_RACE_FILE, sep="\t", index=False)

                    rows_affected = mask.sum()
                    st.success(f"✅ Updated {rows_affected} row(s) successfully!")
                    st.rerun()
                else:
                    st.warning("⚠️ No changes specified. Enter at least one new value.")

        else:
            st.info("No Arms Race data found. Configure schedule first.")

# ==========================================
# PAGE 4: VS DUEL MANAGER
# ==========================================
elif page == "VS Duel Manager":
    st.title("⚔️ VS Duel Manager")

    # Display all VS events
    st.subheader("📋 Current VS Duel Schedule")

    if os.path.exists(VS_DUEL_FILE):
        vs_df = pd.read_csv(VS_DUEL_FILE, sep="\t")

        # Group by day and show all tasks per day
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day in days_order:
            day_events = vs_df[vs_df['Day'] == day]
            if not day_events.empty:
                with st.expander(f"**{day}** - {day_events.iloc[0]['Event']}", expanded=False):
                    st.dataframe(day_events[['Event', 'Task', 'Points']], hide_index=True, use_container_width=True)
    else:
        st.warning("VS Duel schedule file not found.")

    st.divider()
    st.subheader("🔧 Bulk Edit VS Tasks")

    with st.expander("Find and Replace Tasks/Points", expanded=False):
        if os.path.exists(VS_DUEL_FILE):
            vs_df = pd.read_csv(VS_DUEL_FILE, sep="\t")

            # Get unique event names
            unique_events = sorted(vs_df['Event'].unique().tolist())

            col1, col2 = st.columns(2)
            with col1:
                st.write("### Find")
                find_event = st.selectbox("Select Event to Modify", unique_events, key="vs_find_event")

                # Show current occurrences with tasks
                matching_rows = vs_df[vs_df['Event'] == find_event]
                st.write(f"**Found {len(matching_rows)} task(s) for {find_event}:**")

                # Display with all details
                display_df = matching_rows[['Day', 'Task', 'Points']].copy()
                display_df = display_df.sort_values(['Day'])
                st.dataframe(display_df, hide_index=True, use_container_width=True)

            with col2:
                st.write("### Replace With")
                new_event_name = st.text_input("New Event Name (leave blank to keep)", value="", key="vs_new_event")
                new_task_name = st.text_input("New Task Name (leave blank to keep)", value="", key="vs_new_task")
                new_points = st.text_input("New Points (leave blank to keep)", value="", key="vs_new_points")

                st.write("### Apply To")
                apply_scope = st.radio(
                    "Scope",
                    ["All occurrences", "Specific day only", "Specific task only"],
                    key="vs_apply_scope"
                )

                if apply_scope == "Specific day only":
                    days_with_event = sorted(matching_rows['Day'].unique().tolist())
                    specific_day = st.selectbox("Select Day", days_with_event, key="vs_specific_day")
                elif apply_scope == "Specific task only":
                    tasks_list = matching_rows['Task'].unique().tolist()
                    specific_task = st.selectbox("Select Task", tasks_list, key="vs_specific_task")

            if st.button("🔄 Apply Changes", type="primary", use_container_width=True, key="vs_apply"):
                changes_made = False

                # Create a copy to modify
                updated_df = vs_df.copy()

                # Determine which rows to update
                if apply_scope == "All occurrences":
                    mask = updated_df['Event'] == find_event
                elif apply_scope == "Specific day only":
                    mask = (updated_df['Event'] == find_event) & (updated_df['Day'] == specific_day)
                else:  # Specific task only
                    mask = (updated_df['Event'] == find_event) & (updated_df['Task'] == specific_task)

                # Apply changes
                if new_event_name:
                    updated_df.loc[mask, 'Event'] = new_event_name
                    changes_made = True

                if new_task_name:
                    updated_df.loc[mask, 'Task'] = new_task_name
                    changes_made = True

                if new_points:
                    updated_df.loc[mask, 'Points'] = new_points
                    changes_made = True

                if changes_made:
                    # Save back to file
                    updated_df.to_csv(VS_DUEL_FILE, sep="\t", index=False)

                    rows_affected = mask.sum()
                    st.success(f"✅ Updated {rows_affected} row(s) successfully!")
                    st.rerun()
                else:
                    st.warning("⚠️ No changes specified. Enter at least one new value.")

        else:
            st.info("No VS Duel data found.")

# ==========================================
# PAGE 5: SPECIAL EVENTS MANAGER
# ==========================================
elif page == "Special Events Manager":
    st.title("📅 Special Events Manager")
    RESTORE_SPECIAL = "data/restore_special_events.csv"
    specials_df = get_special_events()

    if 'edit_event' not in st.session_state: st.session_state.edit_event = None

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
        freq = c3.selectbox("Frequency", ["weekly", "biweekly"], index=0 if not edit else (0 if edit['freq']=='weekly' else 1))

        current_parity = now_utc.week_of_year % 2
        c4, c5, c6 = st.columns(3)
        starts_this_week = c4.selectbox("Starts this week?", ["Yes", "No"], index=0 if not edit or (int(edit['ref_week'])%2 == current_parity) else 1) if freq == "biweekly" else "Yes"

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
            except: pass

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
            if cols[2].button("📝", key=f"ed_{idx}"): st.session_state.edit_event = row.to_dict(); st.rerun()
            if cols[3].button("🗑️", key=f"dl_{idx}"): specials_df.drop(idx).to_csv(SPECIAL_FILE, sep="\t", index=False); st.rerun()

# ==========================================
# PAGE 6: DAILY TASKS MANAGER
# ==========================================
elif page == "Daily Tasks Manager":
    st.title("📋 Daily Tasks Manager")
    templates_df = get_daily_templates()
    active_df = get_active_tasks()

    if 'edit_template' not in st.session_state: st.session_state.edit_template = None

    # Section 1: Template Management
    st.header("📝 Task Templates")

    col_header, col_actions = st.columns([4, 2])
    with col_actions:
        c_clear, c_restore = st.columns(2)
        if c_clear.button("🧹 Clear Fields", use_container_width=True):
            st.session_state.edit_template = None
            st.rerun()
        if c_restore.button("🔄 Restore Defaults", use_container_width=True):
            if os.path.exists(RESTORE_TEMPLATES_FILE):
                # Load current templates (includes custom)
                current_df = get_daily_templates()
                custom_tasks = current_df[current_df['is_default'].astype(str).str.lower() == 'false']

                # Load default templates
                restore_df = pd.read_csv(RESTORE_TEMPLATES_FILE, sep="\t")

                # Merge: defaults + custom (preserve user's custom tasks)
                merged_df = pd.concat([restore_df, custom_tasks], ignore_index=True)
                merged_df.to_csv(DAILY_TEMPLATES_FILE, sep="\t", index=False)
                st.success("Default templates restored. Custom templates preserved.")
                st.rerun()

    with st.form("template_editor"):
        edit = st.session_state.edit_template
        is_editing_default = edit and str(edit.get('is_default', 'false')).lower() == 'true'

        if edit:
            if is_editing_default:
                st.write("### 📝 Edit Default Task")
                st.info("💡 Editing a default task. Use 'Restore Defaults' to revert changes.")
            else:
                st.write("### 📝 Edit Custom Task")
        else:
            st.write("### ➕ Add New Task")

        c1, c2 = st.columns(2)
        name = c1.text_input("Task Name", value=edit['name'] if edit else "")
        max_daily = c2.number_input("Max Daily Activations", min_value=1, max_value=50, value=int(edit['max_daily']) if edit else 5, key="max_daily", help="How many times per day this task can be activated")

        st.write("**Duration by Rarity Level (minutes)** _(Set to 0 to disable a level, max 6 hours)_")
        d1, d2, d3, d4, d5 = st.columns(5)
        duration_n = d1.number_input("N", min_value=0, max_value=360, value=int(edit['duration_n']) if edit else 10, key="dur_n", help="0 = not applicable")
        duration_r = d2.number_input("R", min_value=0, max_value=360, value=int(edit['duration_r']) if edit else 20, key="dur_r", help="0 = not applicable")
        duration_sr = d3.number_input("SR", min_value=0, max_value=360, value=int(edit['duration_sr']) if edit else 30, key="dur_sr", help="0 = not applicable")
        duration_ssr = d4.number_input("SSR", min_value=0, max_value=360, value=int(edit['duration_ssr']) if edit else 45, key="dur_ssr", help="0 = not applicable")
        duration_ur = d5.number_input("UR", min_value=0, max_value=360, value=int(edit['duration_ur']) if edit else 60, key="dur_ur", help="0 = not applicable")

        c3, c4, c5 = st.columns(3)
        category = c3.text_input("Category", value=edit['category'] if edit else "Custom")

        # Icon selector with preset options
        icon_options = {
            "🎯 Target": "🎯",
            "⚔️ Crossed Swords": "⚔️",
            "🗡️ Dagger": "🗡️",
            "💥 Explosion": "💥",
            "🔫 Pistol": "🔫",
            "🚚 Truck": "🚚",
            "📦 Package": "📦",
            "⛏️ Pickaxe": "⛏️",
            "🌾 Grain": "🌾",
            "💰 Money Bag": "💰",
            "🏰 Castle": "🏰",
            "🛡️ Shield": "🛡️",
            "🏛️ Monument": "🏛️",
            "🚧 Construction": "🚧",
            "🤝 Handshake": "🤝",
            "👥 People": "👥",
            "💬 Chat": "💬",
            "🏆 Trophy": "🏆",
            "⭐ Star": "⭐",
            "🎮 Game": "🎮",
            "⚡ Lightning": "⚡",
            "🔥 Fire": "🔥",
            "📅 Calendar": "📅"
        }

        # Find current icon in options or use custom
        current_icon = edit['icon'] if edit else "⭐"
        icon_labels = list(icon_options.keys())
        icon_values = list(icon_options.values())

        if current_icon in icon_values:
            default_idx = icon_values.index(current_icon)
        else:
            default_idx = 0

        selected_icon_label = c4.selectbox("Icon", icon_labels, index=default_idx, key="icon_select")
        icon = icon_options[selected_icon_label]

        color = c5.color_picker("Color", value=edit['color_code'] if edit else "#9e9e9e")

        if st.form_submit_button("💾 Save Template"):
            if name:
                # Validate at least one level has duration > 0
                if duration_n == 0 and duration_r == 0 and duration_sr == 0 and duration_ssr == 0 and duration_ur == 0:
                    st.error("At least one rarity level must have a duration greater than 0.")
                # Check for duplicate names (excluding current edit)
                elif name in templates_df[templates_df['name'] != (edit['name'] if edit else "")]['name'].tolist():
                    st.error(f"Template '{name}' already exists. Please choose a different name.")
                else:
                    # Preserve is_default flag if editing, otherwise set to false
                    is_default_value = edit.get('is_default', 'false') if edit else 'false'

                    new_template = pd.DataFrame([{
                        'name': name,
                        'duration_n': duration_n,
                        'duration_r': duration_r,
                        'duration_sr': duration_sr,
                        'duration_ssr': duration_ssr,
                        'duration_ur': duration_ur,
                        'max_daily': max_daily,
                        'category': category,
                        'color_code': color,
                        'icon': icon,
                        'is_default': is_default_value
                    }])

                    # Remove old template if editing
                    if edit:
                        templates_df = templates_df[templates_df['name'] != edit['name']]

                    templates_df = pd.concat([templates_df, new_template], ignore_index=True)
                    templates_df.to_csv(DAILY_TEMPLATES_FILE, sep="\t", index=False)
                    st.session_state.edit_template = None
                    st.success(f"Template '{name}' saved.")
                    st.rerun()
            else:
                st.error("Task name is required.")

    st.divider()

    # Display all templates (default and custom together)
    st.write(f"### 📋 Task Templates ({len(templates_df)})")
    if templates_df.empty:
        st.info("No task templates. Use Restore Defaults to load default tasks or create a new one above.")
    else:
        for idx, task in templates_df.iterrows():
            with st.container(border=True):
                dur_n = int(task['duration_n'])
                dur_r = int(task['duration_r'])
                dur_sr = int(task['duration_sr'])
                dur_ssr = int(task['duration_ssr'])
                dur_ur = int(task['duration_ur'])
                max_daily = int(task['max_daily'])

                # Calculate daily activation count
                activations_today = get_daily_activation_count(task['name'], now_server)
                remaining = max_daily - activations_today
                can_activate = remaining > 0

                # Build list of available levels (duration > 0)
                available_levels = []
                if dur_n > 0: available_levels.append(('N', dur_n))
                if dur_r > 0: available_levels.append(('R', dur_r))
                if dur_sr > 0: available_levels.append(('SR', dur_sr))
                if dur_ssr > 0: available_levels.append(('SSR', dur_ssr))
                if dur_ur > 0: available_levels.append(('UR', dur_ur))

                # Check if task has level variants
                has_multiple_levels = len(available_levels) > 1

                if has_multiple_levels:
                    cols = st.columns([2, 2, 2, 1, 1])
                    cols[0].write(f"{task['icon']} **{task['name']}**")
                    cols[1].write(f"📂 {task['category']} | 📊 {remaining}/{max_daily} left")

                    # Create buttons for available levels only
                    num_levels = len(available_levels)
                    level_buttons = cols[2].columns(num_levels)

                    for btn_idx, (level_name, duration) in enumerate(available_levels):
                        if level_buttons[btn_idx].button(level_name, key=f"act_tpl_{level_name}_{idx}", use_container_width=True, help=f"{duration}m", disabled=not can_activate):
                            now_utc_time = pendulum.now('UTC')
                            end_time = now_utc_time.add(minutes=duration)
                            task_id = f"{task['name']}_{now_utc_time.int_timestamp}"

                            new_active = pd.DataFrame([{
                                'task_id': task_id,
                                'task_name': f"{task['name']} ({level_name})",
                                'start_time_utc': now_utc_time.to_iso8601_string(),
                                'duration_minutes': duration,
                                'end_time_utc': end_time.to_iso8601_string(),
                                'status': 'active'
                            }])

                            active_df = pd.concat([active_df, new_active], ignore_index=True)
                            active_df.to_csv(ACTIVE_TASKS_FILE, sep="\t", index=False)
                            st.success(f"✅ {task['name']} ({level_name}) activated!")
                            st.rerun()

                    if cols[3].button("📝", key=f"edit_tpl_{idx}"):
                        st.session_state.edit_template = task.to_dict()
                        st.rerun()

                    if cols[4].button("🗑️", key=f"del_tpl_{idx}"):
                        templates_df = templates_df[templates_df['name'] != task['name']]
                        templates_df.to_csv(DAILY_TEMPLATES_FILE, sep="\t", index=False)
                        st.success(f"Template '{task['name']}' deleted.")
                        st.rerun()

                elif len(available_levels) == 1:
                    # Single level - simple activation button
                    level_name, duration = available_levels[0]
                    cols = st.columns([2, 2, 1, 1, 1])
                    cols[0].write(f"{task['icon']} **{task['name']}**")
                    cols[1].write(f"⏱️ {duration}m | 📂 {task['category']} | 📊 {remaining}/{max_daily} left")

                    if cols[2].button("▶️", key=f"act_tpl_{idx}", disabled=not can_activate):
                        now_utc_time = pendulum.now('UTC')
                        end_time = now_utc_time.add(minutes=duration)
                        task_id = f"{task['name']}_{now_utc_time.int_timestamp}"

                        new_active = pd.DataFrame([{
                            'task_id': task_id,
                            'task_name': task['name'],
                            'start_time_utc': now_utc_time.to_iso8601_string(),
                            'duration_minutes': duration,
                            'end_time_utc': end_time.to_iso8601_string(),
                            'status': 'active'
                        }])

                        active_df = pd.concat([active_df, new_active], ignore_index=True)
                        active_df.to_csv(ACTIVE_TASKS_FILE, sep="\t", index=False)
                        st.success(f"✅ {task['name']} activated!")
                        st.rerun()

                    if cols[3].button("📝", key=f"edit_tpl_sl_{idx}"):
                        st.session_state.edit_template = task.to_dict()
                        st.rerun()

                    if cols[4].button("🗑️", key=f"del_tpl_sl_{idx}"):
                        templates_df = templates_df[templates_df['name'] != task['name']]
                        templates_df.to_csv(DAILY_TEMPLATES_FILE, sep="\t", index=False)
                        st.success(f"Template '{task['name']}' deleted.")
                        st.rerun()

                else:
                    # No valid levels (all durations are 0) - show info message
                    cols = st.columns([2, 2, 1, 1, 1])
                    cols[0].write(f"{task['icon']} **{task['name']}**")
                    cols[1].write(f"📂 {task['category']} | ⚠️ No levels configured")

                    if cols[3].button("📝", key=f"edit_tpl_nv_{idx}"):
                        st.session_state.edit_template = task.to_dict()
                        st.rerun()

                    if cols[4].button("🗑️", key=f"del_tpl_nv_{idx}"):
                        templates_df = templates_df[templates_df['name'] != task['name']]
                        templates_df.to_csv(DAILY_TEMPLATES_FILE, sep="\t", index=False)
                        st.success(f"Template '{task['name']}' deleted.")
                        st.rerun()

# ==========================================
# PAGE 7: SPEED-UP CALCULATOR
# ==========================================
elif page == "Speed-Up Calculator":
    st.title("⏩ Speed-Up Calculator")
    st.caption("Enter a base activity duration and add speed-up items to see how much time remains.")

    # --- Base Activity card ---
    with st.container(border=True):
        st.subheader("Base Activity")
        su_activity_type = st.selectbox(
            "Activity Type",
            ["Training", "Research", "Construction", "Other"],
            key="su_activity_type"
        )
        dur_cols = st.columns(3)
        su_days  = dur_cols[0].number_input("Days",    min_value=0, value=0, step=1, key="su_base_days")
        su_hours = dur_cols[1].number_input("Hours",   min_value=0, value=0, step=1, key="su_base_hours")
        su_mins  = dur_cols[2].number_input("Minutes", min_value=0, value=0, step=1, key="su_base_mins")

    base_total_minutes = su_days * 1440 + su_hours * 60 + su_mins

    # Denominations available in the game (shared by both pools)
    su_denoms = [
        ("8 Hours", 480),
        ("1 Hour",   60),
        ("15 Min",   15),
        ("5 Min",     5),
        ("1 Min",     1),
    ]

    # --- General Speed-Ups card ---
    with st.container(border=True):
        st.subheader("General Speed-Ups")
        gen_cols = st.columns(5)
        gen_quantities = []
        for i, (label, _) in enumerate(su_denoms):
            qty = gen_cols[i].number_input(label, min_value=0, value=0, step=1, key=f"su_gen_qty_{i}")
            gen_quantities.append(qty)

    # --- Typed Speed-Ups card (type is driven by Base Activity) ---
    with st.container(border=True):
        st.subheader(f"{su_activity_type} Speed-Ups")
        typ_cols = st.columns(5)
        typ_quantities = []
        for i, (label, _) in enumerate(su_denoms):
            qty = typ_cols[i].number_input(label, min_value=0, value=0, step=1, key=f"su_typ_qty_{i}")
            typ_quantities.append(qty)

    # --- Calculations ---
    gen_total             = sum(qty * mins for qty, (_, mins) in zip(gen_quantities, su_denoms))
    typ_total             = sum(qty * mins for qty, (_, mins) in zip(typ_quantities, su_denoms))
    speedup_total_minutes = gen_total + typ_total
    remaining_minutes     = max(base_total_minutes - speedup_total_minutes, 0)
    leftover_minutes      = max(speedup_total_minutes - base_total_minutes, 0)
    pct_covered           = (speedup_total_minutes / base_total_minutes * 100) if base_total_minutes > 0 else 0

    # How much of each pool actually gets used (typed first, general fills the rest)
    typed_applied   = min(typ_total, base_total_minutes)
    general_applied = min(gen_total, max(base_total_minutes - typ_total, 0))

    # --- Results ---
    st.divider()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Base Duration",                  format_duration(base_total_minutes))
    m2.metric(f"{su_activity_type} Used",       format_duration(typed_applied))
    m3.metric("General Used",                   format_duration(general_applied))
    m4.metric("Time Remaining",                 format_duration(remaining_minutes))

    # --- Progress bar + status ---
    if base_total_minutes == 0:
        st.warning("Enter a base duration above to start calculating.")
    else:
        # Color thresholds: red < 50 %, amber 50–99 %, green >= 100 %
        if pct_covered >= 100:
            bar_color = "#28a745"
        elif pct_covered >= 50:
            bar_color = "#ffc107"
        else:
            bar_color = "#dc3545"

        bar_width = min(pct_covered, 100)
        st.html(f"""
            <div style="width:100%; background:#e9ecef; border-radius:8px; height:28px; overflow:hidden;">
              <div style="width:{bar_width}%; background:{bar_color}; height:100%; border-radius:8px;
                         transition:width 0.3s ease; display:flex; align-items:center; padding-left:10px;">
                <span style="color:#fff; font-weight:bold; font-size:14px;">{pct_covered:.0f}%</span>
              </div>
            </div>
        """)

        if pct_covered >= 100:
            st.success(f"Fully covered! {format_duration(leftover_minutes)} left over.")
        else:
            st.warning(f"Still needs {format_duration(remaining_minutes)} of speed-ups.")

    # --- Speed-Ups Still Needed (greedy breakdown of remaining time) ---
    if remaining_minutes > 0:
        st.divider()
        st.subheader("Speed-Ups Still Needed")
        st.caption("Minimum items to cover the remaining time (largest first):")
        needed_cols = st.columns(5)
        rem = remaining_minutes
        for i, (label, val) in enumerate(su_denoms):
            count = int(rem // val)
            rem  -= count * val
            needed_cols[i].metric(label, str(count) if count else "—")

# ==========================================
# PAGE 8: SECRETARY BUFFS
# ==========================================
elif page == "Secretary Buffs":
    st.title("🏛️ Secretary Buffs")
    st.caption("Track your timed secretary position. Each hold lasts 5 minutes — set the start time by server clock or queue depth.")

    sec_event = get_secretary_event()

    # --- Active buff banner (auto-clears on expiry) ---
    if sec_event:
        sec_start = pendulum.parse(sec_event['start_time_utc'])
        sec_end   = pendulum.parse(sec_event['end_time_utc'])
        now_check = pendulum.now('UTC')

        if now_check >= sec_end:
            save_secretary_event(None)
            sec_event = None
            st.info("Previous secretary buff expired and was cleared.")
        else:
            sec_type = sec_event['type']
            bonuses  = SECRETARIES[sec_type]['bonuses']
            icon     = SECRETARIES[sec_type]['icon']

            if now_check < sec_start:
                status_str   = f"Starts at {sec_start.in_timezone(user_tz).format(fmt)}"
                status_color = "#1976d2"
            else:
                status_str   = f"Ends at {sec_end.in_timezone(user_tz).format(fmt)}"
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
            """)

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
        sec_info  = SECRETARIES[sec_type]
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
            tgt_cols   = st.columns(2)
            srv_tgt_h  = tgt_cols[0].number_input("Starts — Hour",   min_value=0, max_value=23, value=now_server.hour,   step=1, key="sec_srv_tgt_h")
            srv_tgt_m  = tgt_cols[1].number_input("Starts — Minute", min_value=0, max_value=59, value=now_server.minute, step=1, key="sec_srv_tgt_m")

            # Delta from synced server clock; wraps forward at 24 h
            delta_minutes = (srv_tgt_h * 60 + srv_tgt_m) - (now_server.hour * 60 + now_server.minute)
            if delta_minutes < 0:
                delta_minutes += 1440
            sec_start_time = now_utc.add(minutes=delta_minutes)

            # Server-time end for preview (handle hour wrap)
            srv_end_total  = srv_tgt_h * 60 + srv_tgt_m + 5
            server_preview = f"Server {srv_tgt_h:02d}:{srv_tgt_m:02d}–{(srv_end_total // 60) % 24:02d}:{srv_end_total % 60:02d}"
        else:
            people_ahead = st.number_input(
                "People ahead of you in line",
                min_value=0, value=0, step=1,
                key="sec_people_ahead",
                help="0 = you are up next (buff starts now)."
            )
            sec_start_time  = now_utc.add(minutes=people_ahead * 5)
            server_preview  = ""

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
            'type':           sec_type,
            'start_time_utc': sec_start_time.to_iso8601_string(),
            'end_time_utc':   sec_end_time.to_iso8601_string(),
        })
        st.success(
            f"{SECRETARIES[sec_type]['icon']} {sec_type} set!  "
            f"Active {sec_start_time.in_timezone(user_tz).format(fmt)}–{sec_end_time.in_timezone(user_tz).format(fmt)}."
        )
        st.rerun()

