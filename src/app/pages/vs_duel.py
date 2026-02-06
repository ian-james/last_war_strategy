"""VS Duel Manager page."""

import os
import streamlit as st
import pandas as pd
from app.config.constants import VS_DUEL_FILE


def render(time_ctx: dict):
    """Render the VS Duel Manager page.

    Args:
        time_ctx: Dictionary from setup_timezone_and_time() (not heavily used here)
    """
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
