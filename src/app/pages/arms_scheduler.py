"""Arms Race Scheduler page."""

import os
import streamlit as st
import pandas as pd
import traceback
from app.config.constants import ARMS_RACE_FILE
from app.utils.data_loaders import get_game_data


def render(time_ctx: dict, df: pd.DataFrame):
    """Render the Arms Race Scheduler page.

    Args:
        time_ctx: Dictionary from setup_timezone_and_time() containing:
            - now_server: Current time in server timezone
            - user_tz: User's selected timezone
            - fmt: Time format string
        df: Combined Arms Race + VS Duel schedule dataframe
    """
    now_server = time_ctx['now_server']
    user_tz = time_ctx['user_tz']
    fmt = time_ctx['fmt']

    st.title("🔄 Arms Race Scheduler")
    categories = ["Base Building", "Tech Research", "Drone Boost", "Hero Development", "Unit Progression", "All-Rounder"]
    target_day = st.selectbox("Select Day to Manage", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])

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
            slot_start_srv = now_server.start_of('day').add(hours=(i-1)*4)
            slot_end_srv = slot_start_srv.add(hours=4)
            slot_start_local = slot_start_srv.in_timezone(user_tz).format('HH:mm:ss')
            slot_end_local = slot_end_srv.in_timezone(user_tz).format('HH:mm:ss')

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
                st.code(traceback.format_exc())

    st.divider()
    st.subheader(f"📍 Confirmed {target_day} Schedule")
    final_view_df = get_game_data()
    view_df = final_view_df[(final_view_df['Day'] == target_day) & (final_view_df['Type'] == 'Arms Race')].copy()
    if not view_df.empty:
        view_df = view_df.sort_values('Slot').drop_duplicates(subset=['Slot'])
        # Slot 1 starts at 00:00 server time (= 22:00 Halifax)
        view_df['Time'] = view_df.apply(lambda r: now_server.start_of('day').add(hours=(int(r['Slot'])-1)*4).in_timezone(user_tz).format(fmt), axis=1)
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
