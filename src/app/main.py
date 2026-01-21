import streamlit as st
import pandas as pd
import pendulum
import os

# --- PAGE SETUP ---
st.set_page_config(page_title="Last Standing Tactician", layout="wide", page_icon="🛡️")

def get_game_data():
    paths = ["data/last_standing_schedule.csv", "last_standing_schedule.csv"]
    for path in paths:
        if os.path.exists(path):
            return pd.read_csv(path, sep="\t")
    return None

def highlight_double_dip(row, double_dip_tasks):
    """Applies green background if the task is a double-dip opportunity."""
    is_double = any(row['Task'] == dd['VS Task'] or row['Task'] == dd['AR Task'] for dd in double_dip_tasks)
    if is_double:
        return ['background-color: rgba(0, 255, 0, 0.2)'] * len(row)
    return [''] * len(row)

def main():
    df = get_game_data()
    
    # --- SIDEBAR ---
    st.sidebar.title("🛡️ Command Center")
    user_tz = st.sidebar.selectbox("Local Timezone", ['America/Halifax', 'UTC', 'America/New_York'], index=0)
    time_mode = st.sidebar.radio("Display Format", ["Standard (12h)", "Military (24h)"])
    fmt = "h:mm A" if time_mode == "Standard (12h)" else "HH:mm"

    # --- TIME LOGIC ---
    now_utc = pendulum.now('UTC')
    now_local = pendulum.now(user_tz)
    game_clock = now_utc.subtract(hours=2)
    game_day_name = game_clock.format('dddd')
    current_slot = (game_clock.hour // 4) + 1

    # Sidebar Next Event
    if df is not None:
        next_slot = (current_slot % 6) + 1
        search_day = game_day_name if current_slot < 6 else game_clock.add(days=1).format('dddd')
        next_ev = df[(df['Day'] == search_day) & (df['Slot'] == next_slot)]['Event'].iloc[0]
        st.sidebar.divider()
        st.sidebar.subheader("⏭️ Coming Up Next")
        st.sidebar.info(f"**{next_ev}**")

    # --- TOP METRICS ---
    st.title(f"Last Standing Strategy: {game_day_name}")
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Local Time", now_local.format(fmt), now_local.format('z'))
    with m2: st.metric("Active Game Day", game_day_name)
    with m3:
        target = game_clock.at(hour=((current_slot * 4) % 24), minute=0, second=0)
        if current_slot == 6: target = target.add(days=1)
        rem = target.diff(game_clock)
        st.metric("Next Rotation In", f"{rem.in_hours()}h {rem.in_minutes()%60}m")

    if df is not None:
        df['Points'] = pd.to_numeric(df['Points'], errors='coerce')
        vs_today = df[(df['Day'] == game_day_name) & (df['Type'] == 'VS')].copy()
        ar_active = df[(df['Day'] == game_day_name) & (df['Type'] == 'Arms Race') & (df['Slot'] == current_slot)].copy()
        
        # KEYWORDS for overlap matching
        keywords = ["Speedup", "Research", "Construction", "Hero", "Drone", "T8", "Radar", "UR", "Truck"]
        
        # --- 1. DOUBLE OPPORTUNITIES ---
        st.divider()
        st.subheader("🚀 Double Opportunities (Active Now)")
        double_dip_tasks = []
        if game_day_name != "Sunday":
            for kw in keywords:
                v_m = vs_today[vs_today['Task'].str.contains(kw, case=False)]
                a_m = ar_active[ar_active['Task'].str.contains(kw, case=False)]
                if not v_m.empty and not a_m.empty:
                    for _, v in v_m.iterrows():
                        for _, a in a_m.iterrows():
                            double_dip_tasks.append({"Target": kw, "VS Task": v['Task'], "AR Task": a['Task']})
        
        if double_dip_tasks:
            st.dataframe(pd.DataFrame(double_dip_tasks).drop_duplicates(), hide_index=True, use_container_width=True)
        else:
            st.write("No direct overlaps this hour.")

        # --- 2. OPTIMIZED DAILY PLAN ---
        st.divider()
        st.subheader("📅 Optimized Tactical Plan (Best Times to Play)")
        plan = []
        anchor_utc = now_utc.start_of('day').add(hours=2)
        if now_utc < anchor_utc: anchor_utc = anchor_utc.subtract(days=1)

        for s in range(1, 7):
            start_t = anchor_utc.add(hours=(s-1)*4).in_timezone(user_tz)
            ar_slot = df[(df['Day'] == game_day_name) & (df['Type'] == 'Arms Race') & (df['Slot'] == s)]
            ev_name = ar_slot['Event'].iloc[0]
            
            # Logic: If AR Event Name matches keywords in VS Event Name or Tasks
            is_optimal = any(kw.lower() in ev_name.lower() for kw in keywords)
            
            plan.append({
                "Start Time": start_t.format(fmt),
                "Event": ev_name,
                "Strategy": "💎 HIGH VALUE (Double Points)" if is_optimal else "Standard Value",
                "Action": f"Focus on {ev_name} resources"
            })
        
        st.dataframe(pd.DataFrame(plan), hide_index=True, use_container_width=True)

        # --- 3. ACTIVE ARMS RACE (WITH HIGHLIGHTING) ---
        st.divider()
        st.subheader(f"🔥 Arms Race: {ar_active['Event'].iloc[0]}")
        ar_display = ar_active.sort_values(by='Points', ascending=False)[['Task', 'Points']]
        st.dataframe(ar_display.style.apply(highlight_double_dip, double_dip_tasks=double_dip_tasks, axis=1), 
                     hide_index=True, use_container_width=True)

        # --- 4. VS DUEL (WITH HIGHLIGHTING) ---
        st.divider()
        if not vs_today.empty:
            st.subheader(f"🎯 VS Duel: {vs_today['Event'].iloc[0]}")
            vs_display = vs_today.sort_values(by='Points', ascending=False)[['Task', 'Points']]
            st.dataframe(vs_display.style.apply(highlight_double_dip, double_dip_tasks=double_dip_tasks, axis=1), 
                         hide_index=True, use_container_width=True)

        # --- 5. ROTATIONAL SCHEDULE ---
        st.divider()
        st.subheader("📋 Full Rotation Schedule")
        roadmap = []
        for s in range(1, 7):
            start = anchor_utc.add(hours=(s-1)*4).in_timezone(user_tz)
            ev = df[(df['Day'] == game_day_name) & (df['Slot'] == s)]['Event'].iloc[0]
            roadmap.append({"Time": start.format(fmt), "Event": ev, "Status": "📍 ACTIVE" if s == current_slot else ""})
        st.dataframe(pd.DataFrame(roadmap), hide_index=True, use_container_width=True)

    else:
        st.error("CSV Missing.")

if __name__ == "__main__":
    main()
