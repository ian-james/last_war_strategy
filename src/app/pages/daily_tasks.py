"""Daily Tasks Manager page module."""

import os
import streamlit as st
import pandas as pd
import pendulum
from app.config.constants import (
    DAILY_TEMPLATES_FILE,
    ACTIVE_TASKS_FILE,
    RESTORE_TEMPLATES_FILE,
)
from app.utils.data_loaders import get_daily_templates, get_active_tasks
from app.utils.task_manager import get_daily_activation_count


def render(time_ctx: dict):
    """Render the Daily Tasks Manager page.

    Args:
        time_ctx: Dictionary containing time context with keys:
            - now_server: Current time in server timezone
            - now_utc: Current time in UTC
            - user_tz: User's timezone (pendulum timezone object)
            - user_tz_label: User's timezone label string
            - fmt: Time format string
    """
    # Extract needed values from time_ctx
    now_server = time_ctx['now_server']
    now_utc = time_ctx['now_utc']
    user_tz = time_ctx['user_tz']
    user_tz_label = time_ctx['user_tz_label']
    fmt = time_ctx['fmt']

    st.title("📋 Daily Tasks Manager")
    templates_df = get_daily_templates()
    active_df = get_active_tasks()

    if 'edit_template' not in st.session_state:
        st.session_state.edit_template = None

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
                if dur_n > 0:
                    available_levels.append(('N', dur_n))
                if dur_r > 0:
                    available_levels.append(('R', dur_r))
                if dur_sr > 0:
                    available_levels.append(('SR', dur_sr))
                if dur_ssr > 0:
                    available_levels.append(('SSR', dur_ssr))
                if dur_ur > 0:
                    available_levels.append(('UR', dur_ur))

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
