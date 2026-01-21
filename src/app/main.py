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

def main():
    # --- SIDEBAR CONTROLS ---
    st.sidebar.title("🛡️ Command Center")
    user_tz = st.sidebar.selectbox("Local Timezone", 
                                   ['America/Halifax', 'UTC', 'America/New_York'], 
                                   index=0)
    
    time_mode = st.sidebar.radio("Display Format", ["Standard (12h)", "Military (24h)"])
    fmt = "h:mm A" if time_mode == "Standard (12h)" else "HH:mm"

    # --- TIME & DATE LOGIC (RESTORED) ---
    now_utc = pendulum.now('UTC')
    now_local = pendulum.now(user_tz)
    # Game Reset is 02:00 UTC (10 PM Halifax). Shift UTC by -2 to align day-starts.
    game_clock = now_utc.subtract(hours=2)
    game_day_name = game_clock.format('dddd')
    current_slot = (game_clock.hour // 4) + 1

    # --- TOP DASHBOARD METRICS ---
    st.title(f"Last Standing Strategy: {game_day_name}")
    
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Local Time", now_local.format(fmt), now_local.format('z'))
    with m2:
        st.metric("Active Game Day", game_day_name)
    with m3:
        next_boundary = (current_slot * 4)
        target = game_clock.at(hour=next_boundary % 24, minute=0, second=0)
        if next_boundary >= 24: target = target.add(days=1)
        remaining = target.diff(game_clock)
        st.metric("Next Rotation In", f"{remaining.in_hours()}h {remaining.in_minutes()%60}m")

    df = get_game_data()
    
    if df is not None:
        df['Points'] = pd.to_numeric(df['Points'], errors='coerce')
        
        # Data Filtering
        vs_today = df[(df['Day'] == game_day_name) & (df['Type'] == 'VS')].copy()
        ar_active = df[(df['Day'] == game_day_name) & (df['Type'] == 'Arms Race') & (df['Slot'] == current_slot)].copy()

        # --- 1. DOUBLE OPPORTUNITIES ---
        st.divider()
        st.subheader("🚀 Double Opportunities")
        if game_day_name == "Sunday":
            st.info("Sunday is a Rest Day. No task overlaps.")
        else:
            keywords = ["Speedup", "Research", "Construction", "Hero", "Drone", "T8", "Radar", "UR", "Truck"]
            double_dip_tasks = []

            for kw in keywords:
                vs_m = vs_today[vs_today['Task'].str.contains(kw, case=False)]
                ar_m = ar_active[ar_active['Task'].str.contains(kw, case=False)]
                
                if not vs_m.empty and not ar_m.empty:
                    for _, v in vs_m.iterrows():
                        for _, a in ar_m.iterrows():
                            double_dip_tasks.append({
                                "Target": kw,
                                "VS Task": v['Task'],
                                "AR Task": a['Task']
                            })

            if double_dip_tasks:
                dd_df = pd.DataFrame(double_dip_tasks).drop_duplicates()
                st.dataframe(dd_df, hide_index=True, use_container_width=True)
            else:
                st.write("No direct task overlaps for this hour. Work on individual event goals below.")

        # --- 2. ACTIVE ARMS RACE ---
        st.divider()
        if not ar_active.empty:
            st.subheader(f"🔥 Arms Race: {ar_active['Event'].iloc[0]}")
            ar_display = ar_active.sort_values(by='Points', ascending=False)[['Task', 'Points']]
            st.dataframe(ar_display, hide_index=True, use_container_width=True)

        # --- 3. VS SCORING ---
        st.divider()
        if game_day_name != "Sunday" and not vs_today.empty:
            st.subheader(f"🎯 VS Duel: {vs_today['Event'].iloc[0]}")
            vs_display = vs_today.sort_values(by='Points', ascending=False)[['Task', 'Points']]
            st.dataframe(vs_display, hide_index=True, use_container_width=True)
        else:
            st.subheader("🎯 VS Duel")
            st.success("Enjoy your Sunday break! Prep for Monday Radar.")

        # --- 4. ROTATIONAL SCHEDULE ---
        st.divider()
        st.subheader("📋 Rotational Schedule")
        anchor_utc = now_utc.start_of('day').add(hours=2)
        if now_utc < anchor_utc: anchor_utc = anchor_utc.subtract(days=1)

        roadmap = []
        for s in range(1, 7):
            start = anchor_utc.add(hours=(s-1)*4).in_timezone(user_tz)
            end = start.add(hours=4)
            slot_data = df[(df['Day'] == game_day_name) & (df['Type'] == 'Arms Race') & (df['Slot'] == s)]
            ev_name = slot_data['Event'].iloc[0] if not slot_data.empty else "N/A"
            
            roadmap.append({
                "Time Window": f"{start.format(fmt)} - {end.format(fmt)}",
                "Event": ev_name,
                "Status": "📍 ACTIVE" if s == current_slot else ""
            })
        st.dataframe(pd.DataFrame(roadmap), hide_index=True, use_container_width=True)

    else:
        st.error("Data file 'last_standing_schedule.csv' not found. Please check your data folder.")

if __name__ == "__main__":
    main()
