import streamlit as st
import pandas as pd
import pendulum
import os

# --- SETUP ---
st.set_page_config(page_title="Last Standing Tactician", layout="wide", page_icon="🛡️")
DATA_FILE = "data/last_standing_schedule.csv"
SPECIAL_FILE = "data/special_events.csv"

if not os.path.exists("data"): os.makedirs("data")

# --- DATA HELPERS ---
def get_game_data():
    if os.path.exists(DATA_FILE): return pd.read_csv(DATA_FILE, sep="\t")
    return pd.DataFrame(columns=["Day", "Type", "Slot", "Event", "Task", "Points"])

def get_special_events():
    if os.path.exists(SPECIAL_FILE): return pd.read_csv(SPECIAL_FILE, sep="\t")
    return pd.DataFrame(columns=["name", "days", "freq", "ref_week", "start_time", "end_time"])

def is_event_in_window(event_row, window_start_utc):
    days = str(event_row['days']).split(',')
    if window_start_utc.format('dddd') not in days: return False
    if event_row['freq'] == 'biweekly':
        if (window_start_utc.week_of_year % 2) != (int(event_row['ref_week']) % 2): return False
    win_start, win_end = window_start_utc.format('HH:mm'), window_start_utc.add(hours=4).format('HH:mm')
    return str(event_row['start_time']) < win_end and str(event_row['end_time']) > win_start

# --- TIME LOGIC ---
st.sidebar.title("🛡️ Command Center")
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # 1. Timezone Selection with NA Support
    tz_options = [
        "Select Timezone (N/A)", "America/Halifax", "UTC", "US/Eastern", "US/Central", 
        "US/Mountain", "US/Pacific", "US/Alaska", "US/Hawaii",
        "Canada/Eastern", "Canada/Pacific"
    ]
    selected_tz = st.selectbox("Local Timezone", tz_options, index=0)
    
    if selected_tz == "Select Timezone (N/A)":
        user_tz = "UTC"
        st.info("💡 Defaulting to UTC. Select your zone for local times.")
    else:
        user_tz = selected_tz

    # 2. Time Mode Selection (Fixes the time_mode error)
    time_mode = st.radio("Time Format", ["24h", "12h"], horizontal=True)
    fmt = "HH:mm" if time_mode == "24h" else "h:mm A"

now_utc = pendulum.now('UTC')
now_local = now_utc.in_timezone(user_tz)

# VS Duel at 00:00 UTC | Arms Race offset by 2 hours
vs_day = now_utc.format('dddd')
ar_day = now_utc.subtract(hours=2).format('dddd') 

active_start_utc = now_utc.start_of('day').add(hours=((max(0, now_utc.hour - 2)) // 4) * 4 + 2)
if now_utc.hour < 2: active_start_utc = now_utc.start_of('day').subtract(hours=2)
current_slot = ((active_start_utc.hour - 2) % 24 // 4) + 1

df = get_game_data()
specials_df = get_special_events()
page = st.sidebar.selectbox("Navigate", ["Strategic Dashboard", "Arms Race Scheduler", "Special Events Manager"])

# ==========================================
# PAGE 1: STRATEGIC DASHBOARD
# ==========================================
if page == "Strategic Dashboard":
    game_now = now_utc.subtract(hours=2)
    vs_day = game_now.format('dddd')
    ar_day = game_now.format('dddd')

    st.title(f"🛡️ {vs_day} Tactical Overview")

    # 1. TIMERS
    reset_time = now_utc.start_of('day').add(hours=2)
    if now_utc.hour >= 2: reset_time = reset_time.add(days=1)

    diff_reset = reset_time - now_utc
    next_slot_time = active_start_utc.add(hours=4)
    diff_slot = next_slot_time - now_utc

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📍 Local", now_local.format(fmt))
    m2.metric("🌍 Server (UTC)", now_utc.format("HH:mm"))
    m3.metric("🌙 VS Reset", f"{diff_reset.hours}h {diff_reset.minutes}m")
    m4.metric("📡 AR Slot Ends", f"{diff_slot.hours}h {diff_slot.minutes}m")

    # 2. DATA FETCHING
    vs_active = df[(df['Day'] == vs_day) & (df['Type'] == 'VS')]
    ar_active = df[(df['Day'] == ar_day) & (df['Type'] == 'Arms Race') & (df['Slot'] == current_slot)]

    # 3. OVERLAP MAPPING
    OVERLAP_MAP = {
        "City": ["Building", "Construction", "Speedup"],
        "Base": ["Building", "Construction", "Speedup"],
        "Tech": ["Research", "Speedup"],
        "Hero": ["Hero EXP", "Shard", "Recruitment"],
        "Unit": ["Train", "Soldier", "Speedup"],
        "Drone": ["Drone", "Component"],
        "All-Rounder": ["Hero", "Building", "Research", "Train", "Construction"]
    }

    # 4. SCAN FOR BANNER UPDATES
    next_double = None
    next_drone = None

    for i in range(48):
        scan_t = active_start_utc.add(hours=i*4)
        s_day = scan_t.subtract(hours=2).format('dddd')
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
                ar_row_data = b_ar.iloc[0]
                ar_full_text = (str(ar_ev) + " " + str(ar_row_data['Task'])).lower()
                keywords = OVERLAP_MAP.get(ar_root, [ar_root.lower()])

                overlapping_skills = [
                    str(v_task) for v_task in b_vs['Task']
                    if any(kw.lower() in str(v_task).lower() for kw in keywords)
                    or (any(x in ar_full_text for x in ["building", "construction"]) and 
                        any(x in str(v_task).lower() for x in ["building", "construction"]))
                ]
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

    # 6. 24-HOUR OPTIMIZATION PLAN
    st.subheader("📅 24-Hour Optimization Plan")
    plan_data = []
    for i in range(6):
        b_utc = active_start_utc.add(hours=i*4)
        b_local = b_utc.in_timezone(user_tz)
        b_game_day = b_utc.subtract(hours=2).format('dddd')
        b_slot_n = ((b_utc.hour - 2) % 24 // 4) + 1

        b_ar = df[(df['Day'] == b_game_day) & (df['Type'] == 'Arms Race') & (df['Slot'] == b_slot_n)]
        b_vs = df[(df['Day'] == b_game_day) & (df['Type'] == 'VS')]
        ev_name = b_ar['Event'].iloc[0] if not b_ar.empty else "N/A"

        active_specials = [s_row['name'] for _, s_row in specials_df.iterrows() if is_event_in_window(s_row, b_utc)]
        specials_str = ", ".join(active_specials) if active_specials else "—"

        status = "Regular Value"
        if not b_ar.empty and not b_vs.empty:
            ar_root = ev_name.split()[0]
            ar_full_text = (str(ev_name) + " " + str(b_ar['Task'].iloc[0])).lower()
            keywords = OVERLAP_MAP.get(ar_root, [ar_root.lower()])
            
            for v_task in b_vs['Task']:
                v_low = str(v_task).lower()
                if any(kw.lower() in v_low for kw in keywords) or \
                   (any(x in ar_full_text for x in ["building", "construction"]) and \
                    any(x in v_low for x in ["building", "construction"])):
                    status = "Double Value"
                    break

        plan_data.append({
            "Day": b_local.format('dddd'), "Time": b_local.format(fmt),
            "Arms Race": ev_name, "Special Events": specials_str, "Optimization": status
        })

    def highlight_optimization(row):
        if row.Optimization == "Double Value":
            return ['background-color: #1b5e20; color: #ffffff; font-weight: bold'] * 5
        return [''] * 5

    st.dataframe(pd.DataFrame(plan_data).style.apply(highlight_optimization, axis=1), hide_index=True, use_container_width=True)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**🔥 Current Arms Race: {ar_active['Event'].iloc[0] if not ar_active.empty else 'N/A'}**")
        st.dataframe(ar_active[['Task', 'Points']], hide_index=True, use_container_width=True)
    with c2:
        st.write(f"**🎯 Current VS Duel: {vs_day}**")
        st.dataframe(vs_active[['Task', 'Points']], hide_index=True, use_container_width=True)

# ==========================================
# PAGE 2: ARMS RACE SCHEDULER
# ==========================================
elif page == "Arms Race Scheduler":
    st.title("🔄 Arms Race Scheduler")
    categories = ["City Construction", "Tech Research", "Drone Boost", "Hero Development", "Unit Augmentation", "All-Rounder"]
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
            idx = categories.index(day_map[i]) if day_map[i] in categories else 0
            sel = cols[(i-1)%3].selectbox(f"Slot {i}", categories, index=idx, key=f"s_in_{i}")
            selections.append(sel)

        if st.form_submit_button("💾 Overwrite and Deduplicate"):
            df = df[~((df['Day'] == target_day) & (df['Type'] == 'Arms Race'))]
            new_rows = []
            for i, event_name in enumerate(selections, start=1):
                new_rows.append({"Day": target_day, "Type": "Arms Race", "Slot": i, "Event": event_name, "Task": event_name, "Points": "Standard"})
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            df = df.drop_duplicates(subset=['Day', 'Type', 'Slot'], keep='last')
            df.to_csv(DATA_FILE, sep="\t", index=False)
            st.success(f"Schedule for {target_day} cleaned and updated.")
            st.rerun()

    st.divider()
    st.subheader(f"📍 Confirmed {target_day} Schedule")
    final_view_df = get_game_data()
    view_df = final_view_df[(final_view_df['Day'] == target_day) & (final_view_df['Type'] == 'Arms Race')].copy()
    if not view_df.empty:
        view_df = view_df.sort_values('Slot').drop_duplicates(subset=['Slot'])
        view_df['Time'] = view_df.apply(lambda r: now_utc.start_of('day').add(hours=(int(r['Slot'])-1)*4+2).in_timezone(user_tz).format(fmt), axis=1)
        st.dataframe(view_df[['Time', 'Event']], hide_index=True, use_container_width=True)
    else:
        st.info("No entries found.")

# ==========================================
# PAGE 3: SPECIAL EVENTS MANAGER
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
        
        init_s, init_e = "12:00", "14:00"
        if edit:
            try:
                sh, sm = map(int, edit['start_time'].split(':'))
                eh, em = map(int, edit['end_time'].split(':'))
                init_s = now_utc.at(sh, sm).in_timezone(user_tz).format("HH:mm")
                init_e = now_utc.at(eh, em).in_timezone(user_tz).format("HH:mm")
            except: pass

        s_t = c5.text_input(f"Start Time ({user_tz})", value=init_s)
        e_t = c6.text_input(f"End Time ({user_tz})", value=init_e)

        if st.form_submit_button("💾 Save to File"):
            if name and days:
                final_ref = (current_parity if starts_this_week == "Yes" else 1 - current_parity) if freq == "biweekly" else 0
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
        try:
            sh, sm = map(int, str(row['start_time']).split(':'))
            eh, em = map(int, str(row['end_time']).split(':'))
            l_s, l_e = now_utc.at(sh, sm).in_timezone(user_tz).format(fmt), now_utc.at(eh, em).in_timezone(user_tz).format(fmt)
        except: l_s, l_e = "N/A", "N/A"
        
        with st.container(border=True):
            cols = st.columns([3, 4, 1, 1])
            cols[0].write(f"**{row['name']}**")
            status = "Active" if (row['freq'] == 'weekly' or (int(row['ref_week']) % 2 == current_parity)) else "Inactive"
            cols[1].write(f"🕒 {l_s}-{l_e} | 📅 {row['days']} | {row['freq']} ({status})")
            if cols[2].button("📝", key=f"ed_{idx}"): st.session_state.edit_event = row.to_dict(); st.rerun()
            if cols[3].button("🗑️", key=f"dl_{idx}"): specials_df.drop(idx).to_csv(SPECIAL_FILE, sep="\t", index=False); st.rerun()
