"""Weekly 2× Opportunities Calendar page."""

import streamlit as st
from app.config.constants import OVERLAP_MAP
from app.utils.helpers import word_in_text
from app.utils.data_loaders import get_game_data


def render(time_ctx: dict):
    """Render the Weekly 2× Opportunities Calendar page.

    Args:
        time_ctx: Dictionary from setup_timezone_and_time() containing:
            - now_server: Current time in server timezone
            - user_tz: User's selected timezone
            - fmt: Time format string
    """
    now_server = time_ctx['now_server']
    user_tz = time_ctx['user_tz']
    fmt = time_ctx['fmt']

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

    # Game day resets at midnight server time
    today_game_day = now_server.format('dddd')

    # Rotate so today is first, remaining days follow in order
    today_idx = days_order.index(today_game_day)
    days_order = days_order[today_idx:] + days_order[:today_idx]

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
                            slot_start_srv = now_server.start_of('day').add(hours=(slot-1)*4)
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
