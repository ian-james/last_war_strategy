import streamlit as st
import pandas as pd
import pendulum
import os

# --- PAGE SETUP ---
st.set_page_config(page_title="Last Standing Tactician", layout="wide", page_icon="🛡️")

DATA_FILE = "data/last_standing_schedule.csv"
SPECIAL_FILE = "data/special_events.csv"

# Ensure data directory
if not os.path.exists("data"):
    os.makedirs("data")

# --- DATA LOADERS ---
def get_game_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE, sep="\t")
    # Return default structure if missing
    return pd.DataFrame(columns=["Day", "Type", "Slot", "Event", "Task", "Points"])

def get_special_events():
    if os.path.exists(SPECIAL_FILE):
        return pd.read_csv(SPECIAL_FILE, sep="\t")
    return pd.DataFrame(columns=["name", "days", "freq", "ref_week", "start_time", "end_time"])

def save_game_data(df):
    df.to_csv(DATA_FILE, sep="\t", index=False)

def is_event_in_window(event_row, window_start_utc):
    days = str(event_row['days']).split(',')
    if window_start_utc.format('dddd') not in days: return False
    if event_row['freq'] == 'biweekly':
        if (window_start_utc.week_of_year % 2) != (int(event_row['ref_week']) % 2): return False
    
    win_start = window_start_utc.format('HH:mm')
    win_end = window_start_utc.add(hours=4).format('HH:mm')
    ev_start, ev_end = str(event_row['start_time']), str(event_row['end_time'])
    
    # Simple string comparison works for HH:mm in 24h format
    return ev_start < win_end and ev_end > win_start

# --- SIDEBAR & TIME ---
st.sidebar.title("🛡️ Command Center")
user_tz = st.sidebar.selectbox("Local Timezone", ['America/Halifax', 'UTC', 'America/New_York'], index=0)
time_mode = st.sidebar.radio("Time Format", ["12h", "24h"])
fmt = "h:mm A" if time_mode == "12h" else "HH:mm"
page = st.sidebar.selectbox("Navigate", ["Strategic Dashboard", "Arms Race Scheduler", "Special Events Manager"])

now_utc = pendulum.now('UTC')
now_local = now_utc.in_timezone(user_tz)

# Calculate Game Window (Starts at 02:00 UTC)
# We find the most recent 02, 06, 10, 14, 18, 22 block
active_start_utc = now_utc.start_of('day').add(hours=((now_utc.hour - 2) // 4) * 4 + 2)
if active_start_utc > now_utc: active_start_utc = active_start_utc.subtract(hours=4)

game_day_name = active_start_utc.subtract(hours=2).format('dddd')
current_slot = ((active_start_utc.hour - 2) % 24 // 4) + 1

df = get_game_data()
specials_df = get_special_events()

# ==========================================
# PAGE 1: STRATEGIC DASHBOARD
# ==========================================
if page == "Strategic Dashboard":
    st.title(f"🛡️ {game_day_name} Tactical Overview")

    # 1. UPCOMING SPECIAL EVENTS (Next 24 Hours)
    st.subheader("🔔 Events in Next 24 Hours")
    upcoming = []
    # Check current window + next 5 windows (24h total)
    for i in range(6):
        check_time = active_start_utc.add(hours=i*4)
        for _, row in specials_df.iterrows():
            if is_event_in_window(row, check_time):
                # Avoid duplicates
                if not any(d['Event'] == row['name'] for d in upcoming):
                    local_label = check_time.in_timezone(user_tz)
                    time_label = local_label.format(fmt)
                    day_label = "Today" if local_label.is_today() else local_label.format('dddd')
                    upcoming.append({"Event": row['name'], "Time": f"{day_label} @ {time_label}"})

    if upcoming:
        cols = st.columns(len(upcoming)) if len(upcoming) <= 3 else st.columns(3)
        for i, item in enumerate(upcoming):
            col_idx = i % 3
            cols[col_idx].info(f"**{item['Event']}**\n\n{item['Time']}")
    else:
        st.info("No special events detected in the immediate tactical window.")

    # 2. DOUBLE OPPORTUNITIES
    st.subheader("🚀 Active Double Opportunities")
    double_tasks = []
    vs_today = pd.DataFrame()
    ar_active = pd.DataFrame()

    if not df.empty:
        vs_today = df[(df['Day'] == game_day_name) & (df['Type'] == 'VS')].copy()
        ar_active = df[(df['Day'] == game_day_name) & (df['Type'] == 'Arms Race') & (df['Slot'] == current_slot)].copy()
        for _, ar in ar_active.iterrows():
            match = vs_today[vs_today['Task'].str.contains(ar['Task'], case=False, na=False)]
            if not match.empty:
                for _, m in match.iterrows():
                    double_tasks.append({"AR Stage": ar['Event'], "Task": m['Task'], "VS Points": m['Points']})
    
    if double_tasks:
        st.dataframe(pd.DataFrame(double_tasks), hide_index=True, use_container_width=True)
    else:
        st.success("☕ No task overlaps right now. Great time to gather resources!")

    # 3. TACTICAL PLAN (With Friendly Darker Green)
    st.subheader("📅 24-Hour Optimized Plan")
    plan_data = []
    for i in range(6):
        b_utc = active_start_utc.add(hours=i*4)
        local_win = b_utc.in_timezone(user_tz)
        b_day_name = b_utc.subtract(hours=2).format('dddd')
        
        active_s = [r['name'] for _, r in specials_df.iterrows() if is_event_in_window(r, b_utc)]
        slot_num = ((b_utc.hour - 2) % 24 // 4) + 1
        
        if not df.empty:
            slot_row = df[(df['Day'] == b_day_name) & (df['Type'] == 'Arms Race') & (df['Slot'] == slot_num)]
        else:
            slot_row = pd.DataFrame()

        ev_name = slot_row['Event'].iloc[0] if not slot_row.empty else "N/A"
        
        # High Value Logic
        is_high = any(kw in ev_name for kw in ["Hero", "Unit", "Construction", "Radar"])
        
        plan_data.append({
            "Time": local_win.format(fmt),
            "Arms Race": ev_name,
            "Special Events": " | ".join(active_s) if active_s else "-",
            "Status": "💎 HIGH VALUE" if is_high else "Standard"
        })

    # Styling
    def highlight_row(s):
        # Darker Friendly Green: #2e7d32 (Forest Green) with White Text
        if s.Status == "💎 HIGH VALUE":
            return ['background-color: #2e7d32; color: white'] * len(s)
        return [''] * len(s)

    plan_df = pd.DataFrame(plan_data)
    st.dataframe(plan_df.style.apply(highlight_row, axis=1), hide_index=True, use_container_width=True)

    # 4. FULL LISTS
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**🔥 Arms Race: {ar_active['Event'].iloc[0] if not ar_active.empty else 'N/A'}**")
        if not ar_active.empty: st.dataframe(ar_active[['Task', 'Points']], hide_index=True, use_container_width=True)
    with c2:
        st.write(f"**🎯 VS Duel: {vs_today['Event'].iloc[0] if not vs_today.empty else 'N/A'}**")
        if not vs_today.empty: st.dataframe(vs_today[['Task', 'Points']], hide_index=True, use_container_width=True)

# ==========================================
# PAGE 2: ARMS RACE SCHEDULER
# ==========================================
elif page == "Arms Race Scheduler":
    st.title("🔄 Arms Race Scheduler")
    st.info("Configure the 4-hour rotation for a specific day.")
    
    with st.form("ar_scheduler"):
        target_day = st.selectbox("Select Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        
        # Try to pre-fill if data exists
        defaults = ["City Construction", "Tech Research", "Drone Boost", "Hero Development", "Unit Augmentation", "All-Rounder"]
        if not df.empty:
            existing = df[(df['Day'] == target_day) & (df['Type'] == 'Arms Race')]
            if len(existing) == 6:
                defaults = existing.sort_values('Slot')['Event'].tolist()

        st.write("**Define Events for 4-Hour Slots (UTC Start Times)**")
        cols = st.columns(3)
        s1 = cols[0].text_input("02:00 UTC", value=defaults[0])
        s2 = cols[1].text_input("06:00 UTC", value=defaults[1])
        s3 = cols[2].text_input("10:00 UTC", value=defaults[2])
        s4 = cols[0].text_input("14:00 UTC", value=defaults[3])
        s5 = cols[1].text_input("18:00 UTC", value=defaults[4])
        s6 = cols[2].text_input("22:00 UTC", value=defaults[5])
        
        if st.form_submit_button("💾 Save Schedule"):
            # 1. Remove old entries for this day/type
            if not df.empty:
                df = df[~((df['Day'] == target_day) & (df['Type'] == 'Arms Race'))]
            
            # 2. Add new entries
            new_rows = []
            events = [s1, s2, s3, s4, s5, s6]
            for i, ev in enumerate(events):
                new_rows.append({
                    "Day": target_day,
                    "Type": "Arms Race",
                    "Slot": i + 1,
                    "Event": ev,
                    "Task": ev, # Simplified: Task name = Event name for now
                    "Points": "Standard"
                })
            
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            save_game_data(df)
            st.success(f"Schedule updated for {target_day}!")
            st.rerun()

    # Show current raw data for verification
    st.subheader(f"Current Config for {target_day}")
    if not df.empty:
        st.dataframe(df[(df['Day'] == target_day) & (df['Type'] == 'Arms Race')].sort_values('Slot'), hide_index=True)

# ==========================================
# PAGE 3: SPECIAL EVENTS MANAGER
# ==========================================
elif page == "Special Events Manager":
    st.title("📅 Special Events Manager")
    
    if 'edit_event' not in st.session_state:
        st.session_state.edit_event = None

    # Time Info
    st.info(f"**Local:** {now_local.format(fmt)} ({user_tz}) | **Server:** {now_utc.format('HH:mm')} (UTC)")

    # --- FORM ---
    with st.form("event_editor"):
        edit_data = st.session_state.edit_event
        st.write("### 📝 Edit Event" if edit_data else "### ➕ Add Event")
        
        c1, c2, c3 = st.columns([2, 2, 1])
        name = c1.text_input("Event Name", value=edit_data['name'] if edit_data else "")
        default_days = edit_data['days'].split(',') if edit_data else []
        days = c2.multiselect("Days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], default=default_days)
        freq = c3.selectbox("Frequency", ["weekly", "biweekly"], index=0 if not edit_data else (0 if edit_data['freq']=='weekly' else 1))
        
        c4, c5, c6 = st.columns(3)
        # Pre-fill Logic
        init_s, init_e = "10:00", "14:00"
        if edit_data:
            try:
                sh, sm = map(int, str(edit_data['start_time']).split(':')[:2])
                eh, em = map(int, str(edit_data['end_time']).split(':')[:2])
                init_s = now_utc.at(sh, sm).in_timezone(user_tz).format("HH:mm")
                init_e = now_utc.at(eh, em).in_timezone(user_tz).format("HH:mm")
            except: pass # Fallback if parse fails

        s_t_local = c4.text_input(f"Start Time ({user_tz})", value=init_s)
        e_t_local = c5.text_input(f"End Time ({user_tz})", value=init_e)
        ref = c6.number_input("Ref Week (0 or 1)", value=int(edit_data['ref_week']) if edit_data else 0)
        
        btn_cols = st.columns([1, 1, 4])
        if btn_cols[0].form_submit_button("💾 Save"):
            if name and days:
                try:
                    dummy = pendulum.today(user_tz)
                    # Force set timezone then convert to UTC
                    s_utc = pendulum.parse(f"{dummy.format('YYYY-MM-DD')} {s_t_local}").set(tz=user_tz).in_timezone('UTC').format('HH:mm')
                    e_utc = pendulum.parse(f"{dummy.format('YYYY-MM-DD')} {e_t_local}").set(tz=user_tz).in_timezone('UTC').format('HH:mm')
                    
                    new_row = pd.DataFrame([{"name": name, "days": ",".join(days), "freq": freq, "ref_week": ref, "start_time": s_utc, "end_time": e_utc}])
                    
                    # Update DataFrame
                    if not specials_df.empty:
                        specials_df = specials_df[specials_df['name'] != name]
                    specials_df = pd.concat([specials_df, new_row], ignore_index=True)
                    
                    specials_df.to_csv(SPECIAL_FILE, sep="\t", index=False)
                    st.session_state.edit_event = None
                    st.success("Event Saved!")
                    st.rerun()
                except Exception as e: st.error(f"Time Error: {e}")

        if edit_data and btn_cols[1].form_submit_button("❌ Cancel"):
            st.session_state.edit_event = None
            st.rerun()

    # --- LIST ---
    st.subheader("📋 Current Events")
    if not specials_df.empty:
        for idx, row in specials_df.iterrows():
            try:
                # Robust Display Logic
                if ':' not in str(row['start_time']): continue
                sh, sm = map(int, str(row['start_time']).split(':')[:2])
                eh, em = map(int, str(row['end_time']).split(':')[:2])
                l_s = now_utc.at(sh, sm).in_timezone(user_tz).format(fmt)
                l_e = now_utc.at(eh, em).in_timezone(user_tz).format(fmt)
                
                cols = st.columns([3, 4, 1, 1])
                cols[0].write(f"**{row['name']}**")
                cols[1].write(f"{l_s} - {l_e} ({row['days']})")
                
                if cols[2].button("📝", key=f"ed_{idx}"):
                    st.session_state.edit_event = row.to_dict()
                    st.rerun()
                if cols[3].button("🗑️", key=f"rm_{idx}"):
                    specials_df.drop(idx).to_csv(SPECIAL_FILE, sep="\t", index=False)
                    st.rerun()
            except: continue
