"""Strategic Dashboard page."""

import streamlit as st
import pandas as pd
import pendulum
from app.config.constants import (
    OVERLAP_MAP,
    ACTIVE_TASKS_FILE,
    SLOT_START_HOURS,
)
from app.utils import (
    get_active_tasks,
    get_active_tasks_in_window,
    has_tasks_ending_in_window,
    is_event_in_window,
    get_secretary_event,
    save_secretary_event,
    get_daily_templates,
    get_daily_activation_count,
    word_in_text,
    get_daily_slot_swap,
    save_daily_slot_swap,
    clear_daily_slot_swap,
    can_swap_today,
    apply_slot_swap,
)


def group_tasks_by_base_name(task_names: list) -> list:
    """Group tasks with the same base name and combine their rarity suffixes.

    Example:
        ["Secret Mobile Squad (UR)", "Secret Mobile Squad (SSR)", "Other Task"]
        → ["Secret Mobile Squad (UR, SSR)", "Other Task"]

    Args:
        task_names: List of task name strings

    Returns:
        List of grouped task names
    """
    if not task_names:
        return []

    # Dictionary to group tasks: {base_name: [suffix1, suffix2, ...]}
    grouped = {}

    for task in task_names:
        # Check if task has a rarity suffix in parentheses at the end
        if '(' in task and task.endswith(')'):
            # Split at the last opening parenthesis
            last_paren = task.rfind('(')
            base_name = task[:last_paren].strip()
            suffix = task[last_paren+1:-1].strip()  # Remove '(' and ')'

            if base_name not in grouped:
                grouped[base_name] = []
            grouped[base_name].append(suffix)
        else:
            # Task without rarity suffix, add as-is
            if task not in grouped:
                grouped[task] = []

    # Reconstruct grouped task names
    result = []
    for base_name, suffixes in grouped.items():
        if suffixes:
            # Combine suffixes: "Base Name (S1, S2, S3)"
            combined_suffix = ", ".join(suffixes)
            result.append(f"{base_name} ({combined_suffix})")
        else:
            # No suffix, just the base name
            result.append(base_name)

    return result


def render(time_ctx: dict, df: pd.DataFrame, specials_df: pd.DataFrame):
    """Render the Strategic Dashboard page.

    Args:
        time_ctx: Dictionary containing all time-related values:
            - now_utc, now_server, now_local: pendulum DateTime objects
            - user_tz, server_tz: timezone objects
            - fmt: time format string
            - current_slot: current slot number (1-6)
            - active_start: start of current slot window
            - game_day_start: start of game day (midnight server)
            - vs_day, ar_day: day names (e.g., "Thursday")
            - server_tz_label, user_tz_label: timezone display labels
        df: Combined Arms Race + VS Duel schedule dataframe
        specials_df: Special events dataframe
    """
    # Extract values from time_ctx
    now_utc = time_ctx['now_utc']
    now_server = time_ctx['now_server']
    now_local = time_ctx['now_local']
    user_tz = time_ctx['user_tz']
    fmt = time_ctx['fmt']
    current_slot = time_ctx['current_slot']
    active_start = time_ctx['active_start']
    game_day_start = time_ctx['game_day_start']
    vs_day = time_ctx['vs_day']
    ar_day = time_ctx['ar_day']
    server_tz_label = time_ctx['server_tz_label']
    user_tz_label = time_ctx['user_tz_label']

    # Apply daily slot swap if one exists for today
    df = apply_slot_swap(df, ar_day, now_server)

    # Debug toggle
    if 'show_debug' not in st.session_state:
        st.session_state.show_debug = False

    col_title, col_refresh, col_debug = st.columns([3, 1, 1])
    with col_title:
        st.title(f"🛡️ {vs_day} Tactical Overview")
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True, type="primary"):
            st.rerun()
    with col_debug:
        if st.button("🐛 Debug" if not st.session_state.show_debug else "✅ Debug",
                     use_container_width=True,
                     type="secondary" if not st.session_state.show_debug else "primary"):
            st.session_state.show_debug = not st.session_state.show_debug
            st.rerun()

    # 1. Auto-reload the dashboard every 60 seconds so all times stay live
    st.html(
        '<script>setTimeout(function(){ location.reload(); }, 60000);</script>'
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

        # Game day resets at midnight server time
        s_day = scan_t.format('dddd')

        # Calculate slot
        slot_n = (scan_t.hour // 4) + 1

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
                <h4 style="color: #0d47a1; margin:0 0 5px 0;">🚀 NEXT DOUBLE VALUE: {next_double['name'] if next_double else 'N/A'}</h4>
                <p style="color: #1565c0; margin:0; font-weight: 600;">Skills: {" | ".join(next_double['skills']) if next_double else 'None'}</p>
                <p style="color: #1565c0; margin:0; font-weight: 500;">Starts {next_double['time'] if next_double else 'N/A'}</p>
            </div>
            <div style="width: 2%; border-left: 1px solid #bbdefb;"></div>
            <div style="width: 48%;">
                <h4 style="color: #0d47a1; margin:0 0 5px 0;">⚡ STAMINA OPTIMIZATION</h4>
                <p style="color: #1565c0; margin:0; font-weight: 600;">Next Drone Boost: {next_drone['time'] if next_drone else 'N/A'}</p>
                <p style="color: #546e7a; margin:0; font-size: 0.8em;">Wait for this window to burn stamina packs.</p>
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

    # 6.5. TACTICAL SLOT SWAP
    swap_available = can_swap_today(now_server)
    current_swap = get_daily_slot_swap()

    # Show swap status
    if current_swap and not swap_available:
        # Active swap exists
        from_slot = current_swap['from_slot']
        to_slot = current_swap['to_slot']
        st.info(f"🔄 **Active Slot Swap Today:** Slot {from_slot} ↔ Slot {to_slot}  |  Resets at 02:00 server time tomorrow")

    if swap_available:
        with st.expander("🔄 **Tactical Slot Swap** (Once Daily)", expanded=False):
            st.caption("Swap the current time slot with another slot for today only. Does not affect your weekly schedule.")

            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.write(f"**Current Slot:** {current_slot}")
                current_ar = df[(df['Day'] == ar_day) & (df['Type'] == 'Arms Race') & (df['Slot'] == current_slot)]
                if not current_ar.empty:
                    st.write(f"📍 {current_ar['Event'].iloc[0]}")
                else:
                    st.write("📍 No event scheduled")

            with col2:
                st.write("**Swap With:**")
                # Get available slots for today (excluding current slot)
                other_slots = [s for s in range(1, 7) if s != current_slot]
                slot_options = {}
                for slot_num in other_slots:
                    slot_ar = df[(df['Day'] == ar_day) & (df['Type'] == 'Arms Race') & (df['Slot'] == slot_num)]
                    event_name = slot_ar['Event'].iloc[0] if not slot_ar.empty else "No event"
                    # Convert slot to server time for display
                    slot_hour = SLOT_START_HOURS[slot_num - 1]
                    slot_time_srv = now_server.start_of('day').add(hours=slot_hour)
                    slot_time_local = slot_time_srv.in_timezone(user_tz).format('HH:mm')
                    slot_options[f"Slot {slot_num} ({slot_time_local}) - {event_name}"] = slot_num

                selected_option = st.selectbox(
                    "Select slot to swap with:",
                    options=list(slot_options.keys()),
                    key="swap_target_slot"
                )
                target_slot = slot_options[selected_option]

            with col3:
                st.write("")  # Spacing
                st.write("")  # Spacing
                if st.button("🔄 Swap Slots", type="primary", use_container_width=True, key="execute_swap"):
                    # Save the swap
                    game_date_str = now_server.format('YYYY-MM-DD')
                    save_daily_slot_swap(current_slot, target_slot, game_date_str)
                    st.success(f"✅ Swapped Slot {current_slot} ↔ Slot {target_slot} for today!")
                    st.info("💡 Refresh to see the updated schedule. Swap resets at 02:00 server time tomorrow.")
                    st.rerun()

    elif current_swap:
        with st.expander("🔄 Manage Today's Slot Swap"):
            from_slot = current_swap['from_slot']
            to_slot = current_swap['to_slot']

            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Active Swap:** Slot {from_slot} ↔ Slot {to_slot}")
                st.caption("This swap is active until 02:00 server time tomorrow")

            with col2:
                if st.button("❌ Cancel Swap", type="secondary", use_container_width=True, key="cancel_swap"):
                    clear_daily_slot_swap()
                    st.success("✅ Slot swap cancelled - schedule restored to normal")
                    st.rerun()

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
        st.write("**Slot boundaries (server):** Slot1=00-04, Slot2=04-08, Slot3=08-12, Slot4=12-16, Slot5=16-20, Slot6=20-00")
        calc_step1 = now_server.hour // 4
        calc_step2 = calc_step1 + 1
        st.write(f"**Formula:** (server_hour // 4) + 1")
        st.write(f"**Step 1:** {now_server.hour} // 4 = {calc_step1}")
        st.write(f"**Step 2:** {calc_step1} + 1 = {calc_step2}")
        st.write(f"**Result: Slot {calc_step2} (global, same for all players)**")

        # Show what this means in local time
        slot_starts = SLOT_START_HOURS
        current_slot_start_srv = slot_starts[calc_step2 - 1]
        current_slot_start_local = now_server.start_of('day').add(hours=current_slot_start_srv).in_timezone(user_tz)
        st.write(f"**In your timezone:** Slot {calc_step2} is {current_slot_start_local.format('HH:mm')}-{current_slot_start_local.add(hours=4).format('HH:mm')} local")

        st.write("### Calculated Slot Info")
        st.write(f"**Current Slot (calculated):** {current_slot}")
        st.write(f"**Current Game Day (calculated):** {ar_day}")
        st.write(f"**Active Window Start (Local):** {active_start.in_timezone(user_tz).format('YYYY-MM-DD HH:mm:ss')}")
        st.write(f"**Active Window End (Local):** {active_start.add(hours=4).in_timezone(user_tz).format('YYYY-MM-DD HH:mm:ss')}")

        st.write("### First Row of Optimization Table (Should be current slot)")
        first_row_srv   = active_start
        first_row_local = first_row_srv.in_timezone(user_tz)
        first_row_day  = first_row_srv.format('dddd')
        first_row_slot = (first_row_srv.hour // 4) + 1

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

        # Game day resets at midnight server time
        b_game_day = b_srv.format('dddd')

        # Slot from server-time hour
        b_slot_n = (b_srv.hour // 4) + 1

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
        # Group tasks with the same base name (e.g., "Secret Mobile Squad (UR, SSR)")
        grouped_tasks = group_tasks_by_base_name(active_daily_tasks)
        daily_tasks_str = ", ".join(grouped_tasks) if grouped_tasks else ""

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
            "Day": b_game_day, "Time": f"{b_local.format(fmt)}–{b_local.add(hours=4).format(fmt)}",
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
            b_game_day = b_srv.format('dddd')
            b_slot_n = (b_srv.hour // 4) + 1
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
        <div style="padding: 14px 10px; margin: 2px 0; display: flex; align-items: center; gap: 25px; font-weight: bold; font-size: 1.1em;">
            <div style="width: 80px; flex-shrink: 0;">Day</div>
            <div style="width: 140px; flex-shrink: 0;">Time</div>
            <div style="width: 140px; flex-shrink: 0;">Arms Race</div>
            <div style="flex: 1; min-width: 80px;">Special Events</div>
            <div style="flex: 1; min-width: 80px;">Daily Tasks</div>
            <div style="width: 60px; flex-shrink: 0;">Value</div>
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
        now_badge = '<span style="background:#1976d2; color:white; font-size:0.8em; font-weight:bold; padding:2px 6px; border-radius:3px; margin-left:4px;">◀ NOW</span>' if is_current else ''
        border_left = "border-left: 4px solid #1976d2;" if is_current else ""
        row_style = f"background-color: {bg_color}; color: {text_color}; {border_left}" if bg_color else f"background-color: transparent; color: inherit; {border_left}"

        # Put the row content and button on the same line
        content_col, btn_col = st.columns([95, 5])

        with content_col:
            row_html = f"""
            <div style="{row_style} padding: 14px 10px; margin: 2px 0; border-radius: 4px; display: flex; align-items: center; gap: 25px;">
                <div style="width: 80px; flex-shrink: 0; font-size: 1.05em;">{row_data["Day"]}</div>
                <div style="width: 140px; flex-shrink: 0; font-size: 1.05em;">{row_data["Time"]}{now_badge}</div>
                <div style="width: 140px; flex-shrink: 0; font-size: 1.05em;">{row_data["Arms Race"]}</div>
                <div style="flex: 1; min-width: 80px; font-size: 1.0em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{special_events_content}</div>
                <div style="flex: 1; min-width: 80px; font-size: 1.0em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{daily_tasks_content}</div>
                <div style="width: 60px; flex-shrink: 0; font-size: 1.05em;">{row_data["Optimization"]}</div>
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
