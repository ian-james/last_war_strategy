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
from app.utils.task_manager import (
    get_daily_activation_count,
    is_checkbox_done_today,
    uncheck_task_today,
    complete_checkbox_task,
    ARMS_RACE_CATEGORIES,
)

ARMS_RACE_CATEGORY_OPTIONS = [""] + ARMS_RACE_CATEGORIES


def render(time_ctx: dict):
    """Render the Daily Tasks Manager page."""
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

    # --- Section 1: Template Management ---
    st.header("📝 Task Templates")

    col_header, col_actions = st.columns([4, 2])
    with col_actions:
        c_clear, c_restore = st.columns(2)
        if c_clear.button("🧹 Clear Fields", use_container_width=True):
            st.session_state.edit_template = None
            st.rerun()
        if c_restore.button("🔄 Restore Defaults", use_container_width=True):
            if os.path.exists(RESTORE_TEMPLATES_FILE):
                current_df = get_daily_templates()
                custom_tasks = current_df[current_df['is_default'].astype(str).str.lower() == 'false']
                restore_df = pd.read_csv(RESTORE_TEMPLATES_FILE, sep="\t")
                if 'task_type' not in restore_df.columns:
                    restore_df['task_type'] = 'timed'
                if 'arms_race_category' not in restore_df.columns:
                    restore_df['arms_race_category'] = ''
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

        # --- Task type selector ---
        edit_type = edit.get('task_type', 'timed') if edit else 'timed'
        if edit_type not in ('timed', 'checkbox'):
            edit_type = 'timed'
        task_type = st.radio(
            "Task Type",
            options=["timed", "checkbox"],
            index=0 if edit_type == 'timed' else 1,
            format_func=lambda x: "⏱️ Timed (Rarity-based timer)" if x == "timed" else "☑️ Checkbox (Done / Not Done)",
            horizontal=True,
            help="Timed tasks start a countdown timer per rarity level. Checkbox tasks are simply marked done once per day."
        )

        c1, c2 = st.columns(2)
        name = c1.text_input("Task Name", value=edit['name'] if edit else "")
        max_daily = c2.number_input(
            "Max Daily Activations",
            min_value=1, max_value=50,
            value=int(edit['max_daily']) if edit else (1 if task_type == 'checkbox' else 5),
            key="max_daily",
            help="How many times per day this task can be activated (checkbox tasks are usually 1)"
        )

        # --- Rarity durations (timed only) ---
        if task_type == 'timed':
            st.write("**Duration by Rarity Level (minutes)** _(Set to 0 to disable a level, max 6 hours)_")
            d1, d2, d3, d4, d5 = st.columns(5)
            duration_n   = d1.number_input("N",   min_value=0, max_value=360, value=int(edit['duration_n'])   if edit else 10,  key="dur_n",   help="0 = not applicable")
            duration_r   = d2.number_input("R",   min_value=0, max_value=360, value=int(edit['duration_r'])   if edit else 20,  key="dur_r",   help="0 = not applicable")
            duration_sr  = d3.number_input("SR",  min_value=0, max_value=360, value=int(edit['duration_sr'])  if edit else 30,  key="dur_sr",  help="0 = not applicable")
            duration_ssr = d4.number_input("SSR", min_value=0, max_value=360, value=int(edit['duration_ssr']) if edit else 45,  key="dur_ssr", help="0 = not applicable")
            duration_ur  = d5.number_input("UR",  min_value=0, max_value=360, value=int(edit['duration_ur'])  if edit else 60,  key="dur_ur",  help="0 = not applicable")
        else:
            duration_n = duration_r = duration_sr = duration_ssr = duration_ur = 0

        c3, c4, c5 = st.columns(3)

        # Arms Race category (always visible; required for checkbox, optional for timed)
        edit_arc = edit.get('arms_race_category', '') if edit else ''
        if pd.isna(edit_arc):
            edit_arc = ''
        arc_label = "Arms Race Category" if task_type == 'timed' else "Arms Race Category *(blank = Anytime)*"
        arc_idx = ARMS_RACE_CATEGORY_OPTIONS.index(edit_arc) if edit_arc in ARMS_RACE_CATEGORY_OPTIONS else 0
        arms_race_category = c3.selectbox(
            arc_label,
            options=ARMS_RACE_CATEGORY_OPTIONS,
            index=arc_idx,
            key="arms_race_cat",
            help="Link this task to an Arms Race event so it shows up during that slot."
        )

        # Icon selector
        icon_options = {
            "🎯 Target": "🎯", "⚔️ Crossed Swords": "⚔️", "🗡️ Dagger": "🗡️",
            "💥 Explosion": "💥", "🔫 Pistol": "🔫", "🚚 Truck": "🚚",
            "📦 Package": "📦", "⛏️ Pickaxe": "⛏️", "🌾 Grain": "🌾",
            "💰 Money Bag": "💰", "🏰 Castle": "🏰", "🛡️ Shield": "🛡️",
            "🏛️ Monument": "🏛️", "🚧 Construction": "🚧", "🤝 Handshake": "🤝",
            "👥 People": "👥", "💬 Chat": "💬", "🏆 Trophy": "🏆",
            "⭐ Star": "⭐", "🎮 Game": "🎮", "⚡ Lightning": "⚡",
            "🔥 Fire": "🔥", "📅 Calendar": "📅", "☑️ Checkbox": "☑️",
            "🔬 Research": "🔬", "🏗️ Construction": "🏗️", "⚗️ Science": "⚗️",
        }
        current_icon = edit['icon'] if edit else ("☑️" if task_type == 'checkbox' else "⭐")
        icon_labels = list(icon_options.keys())
        icon_values = list(icon_options.values())
        default_idx = icon_values.index(current_icon) if current_icon in icon_values else 0
        selected_icon_label = c4.selectbox("Icon", icon_labels, index=default_idx, key="icon_select")
        icon = icon_options[selected_icon_label]

        # Category text field (internal grouping, separate from arms_race_category)
        category = c5.text_input(
            "Internal Category",
            value=edit['category'] if edit else "Custom",
            help="Internal label for grouping (e.g. Combat, Resources)"
        )

        color = st.color_picker("Color", value=edit['color_code'] if edit else "#9e9e9e")

        if st.form_submit_button("💾 Save Template"):
            if not name:
                st.error("Task name is required.")
            elif task_type == 'timed' and duration_n == 0 and duration_r == 0 and duration_sr == 0 and duration_ssr == 0 and duration_ur == 0:
                st.error("Timed tasks require at least one rarity level with a duration greater than 0.")
            elif name in templates_df[templates_df['name'] != (edit['name'] if edit else "")]['name'].tolist():
                st.error(f"Template '{name}' already exists. Please choose a different name.")
            else:
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
                    'is_default': is_default_value,
                    'task_type': task_type,
                    'arms_race_category': arms_race_category,
                }])

                if edit:
                    templates_df = templates_df[templates_df['name'] != edit['name']]

                templates_df = pd.concat([templates_df, new_template], ignore_index=True)
                templates_df.to_csv(DAILY_TEMPLATES_FILE, sep="\t", index=False)
                st.session_state.edit_template = None
                st.success(f"Template '{name}' saved.")
                st.rerun()

    st.divider()

    # --- Section 2: Template List ---
    timed_tasks = templates_df[templates_df['task_type'].fillna('timed') == 'timed']
    checkbox_tasks = templates_df[templates_df['task_type'].fillna('timed') == 'checkbox']

    # --- Timed tasks ---
    st.write(f"### ⏱️ Timed Tasks ({len(timed_tasks)})")
    if timed_tasks.empty:
        st.info("No timed task templates. Add one above or use Restore Defaults.")
    else:
        _render_timed_tasks(timed_tasks, templates_df, active_df, now_server, now_utc)

    st.divider()

    # --- Checkbox tasks grouped by Arms Race category ---
    st.write(f"### ☑️ Checkbox Tasks ({len(checkbox_tasks)})")
    if checkbox_tasks.empty:
        st.info("No checkbox tasks. Add one above with Task Type = Checkbox.")
    else:
        _render_checkbox_tasks(checkbox_tasks, templates_df, now_server)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _render_timed_tasks(timed_tasks, templates_df, active_df, now_server, now_utc):
    for idx, task in timed_tasks.iterrows():
        dur_n   = int(task['duration_n'])
        dur_r   = int(task['duration_r'])
        dur_sr  = int(task['duration_sr'])
        dur_ssr = int(task['duration_ssr'])
        dur_ur  = int(task['duration_ur'])
        max_daily = int(task['max_daily'])

        activations_today = get_daily_activation_count(task['name'], now_server)
        remaining = max_daily - activations_today
        can_activate = remaining > 0

        available_levels = []
        if dur_n   > 0: available_levels.append(('N',   dur_n))
        if dur_r   > 0: available_levels.append(('R',   dur_r))
        if dur_sr  > 0: available_levels.append(('SR',  dur_sr))
        if dur_ssr > 0: available_levels.append(('SSR', dur_ssr))
        if dur_ur  > 0: available_levels.append(('UR',  dur_ur))

        arc = task.get('arms_race_category', '')
        arc_badge = f" · 🗓️ {arc}" if arc and not pd.isna(arc) and arc != '' else ""

        with st.container(border=True):
            if len(available_levels) > 1:
                cols = st.columns([2, 2, 2, 1, 1])
                cols[0].write(f"{task['icon']} **{task['name']}**")
                cols[1].write(f"📂 {task['category']}{arc_badge} | 📊 {remaining}/{max_daily} left")

                num_levels = len(available_levels)
                level_buttons = cols[2].columns(num_levels)
                for btn_idx, (level_name, duration) in enumerate(available_levels):
                    if level_buttons[btn_idx].button(
                        level_name, key=f"act_tpl_{level_name}_{idx}",
                        use_container_width=True, help=f"{duration}m",
                        disabled=not can_activate
                    ):
                        _activate_timed_task(task, level_name, duration, now_utc)

                if cols[3].button("📝", key=f"edit_tpl_{idx}"):
                    st.session_state.edit_template = task.to_dict()
                    st.rerun()
                if cols[4].button("🗑️", key=f"del_tpl_{idx}"):
                    _delete_template(task['name'])

            elif len(available_levels) == 1:
                level_name, duration = available_levels[0]
                cols = st.columns([2, 2, 1, 1, 1])
                cols[0].write(f"{task['icon']} **{task['name']}**")
                cols[1].write(f"⏱️ {duration}m | 📂 {task['category']}{arc_badge} | 📊 {remaining}/{max_daily} left")

                if cols[2].button("▶️", key=f"act_tpl_{idx}", disabled=not can_activate):
                    _activate_timed_task(task, level_name, duration, now_utc)

                if cols[3].button("📝", key=f"edit_tpl_sl_{idx}"):
                    st.session_state.edit_template = task.to_dict()
                    st.rerun()
                if cols[4].button("🗑️", key=f"del_tpl_sl_{idx}"):
                    _delete_template(task['name'])

            else:
                cols = st.columns([2, 2, 1, 1])
                cols[0].write(f"{task['icon']} **{task['name']}**")
                cols[1].write(f"📂 {task['category']} | ⚠️ No levels configured")
                if cols[2].button("📝", key=f"edit_tpl_nv_{idx}"):
                    st.session_state.edit_template = task.to_dict()
                    st.rerun()
                if cols[3].button("🗑️", key=f"del_tpl_nv_{idx}"):
                    _delete_template(task['name'])


def _render_checkbox_tasks(checkbox_tasks, templates_df, now_server):
    # Group by Arms Race category
    grouped = checkbox_tasks.groupby('arms_race_category', sort=True, dropna=False)

    for cat, group in grouped:
        cat_label = cat if cat else "Uncategorized"
        st.write(f"**🗓️ {cat_label}**")
        for idx, task in group.iterrows():
            max_daily = int(task['max_daily'])
            activations_today = get_daily_activation_count(task['name'], now_server)
            done = activations_today >= max_daily

            with st.container(border=True):
                cols = st.columns([0.5, 3, 2, 1, 1])

                # Checkbox-style toggle button
                check_icon = "✅" if done else "⬜"
                check_label = "Done" if done else "Mark Done"
                if cols[0].button(check_icon, key=f"chk_{idx}", help=check_label):
                    if done:
                        uncheck_task_today(task['name'])
                        st.rerun()
                    else:
                        complete_checkbox_task(task['name'], now_server)
                        st.success(f"☑️ {task['name']} marked done!")
                        st.rerun()

                status_text = "~~Done today~~" if done else "Pending"
                cols[1].write(f"{task['icon']} **{task['name']}**  \n{status_text}")
                cols[2].write(f"📂 {task['category']} | 📊 {max_daily - activations_today}/{max_daily} left")

                if cols[3].button("📝", key=f"edit_chk_{idx}"):
                    st.session_state.edit_template = task.to_dict()
                    st.rerun()
                if cols[4].button("🗑️", key=f"del_chk_{idx}"):
                    _delete_template(task['name'])

    # Any checkbox tasks without a category
    uncategorized = checkbox_tasks[checkbox_tasks['arms_race_category'].fillna('') == '']
    if not uncategorized.empty and '' not in [g for g, _ in grouped]:
        st.write("**⚠️ Uncategorized Checkbox Tasks**")
        for idx, task in uncategorized.iterrows():
            with st.container(border=True):
                cols = st.columns([4, 1, 1])
                cols[0].write(f"{task['icon']} **{task['name']}** — ⚠️ No Arms Race Category set")
                if cols[1].button("📝", key=f"edit_unc_{idx}"):
                    st.session_state.edit_template = task.to_dict()
                    st.rerun()
                if cols[2].button("🗑️", key=f"del_unc_{idx}"):
                    _delete_template(task['name'])


# ---------------------------------------------------------------------------
# Action helpers
# ---------------------------------------------------------------------------

def _activate_timed_task(task, level_name, duration, now_utc):
    active_df = get_active_tasks()
    now_utc_time = pendulum.now('UTC')
    end_time = now_utc_time.add(minutes=duration)
    task_id = f"{task['name']}_{now_utc_time.int_timestamp}"

    has_multiple_levels = sum(1 for col in ['duration_n', 'duration_r', 'duration_sr', 'duration_ssr', 'duration_ur']
                              if int(task[col]) > 0) > 1

    display_name = f"{task['name']} ({level_name})" if has_multiple_levels else task['name']

    new_active = pd.DataFrame([{
        'task_id': task_id,
        'task_name': display_name,
        'start_time_utc': now_utc_time.to_iso8601_string(),
        'duration_minutes': duration,
        'end_time_utc': end_time.to_iso8601_string(),
        'status': 'active'
    }])

    active_df = pd.concat([active_df, new_active], ignore_index=True)
    active_df.to_csv(ACTIVE_TASKS_FILE, sep="\t", index=False)
    st.success(f"✅ {display_name} activated!")
    st.rerun()


def _delete_template(task_name):
    templates_df = get_daily_templates()
    templates_df = templates_df[templates_df['name'] != task_name]
    templates_df.to_csv(DAILY_TEMPLATES_FILE, sep="\t", index=False)
    st.success(f"Template '{task_name}' deleted.")
    st.rerun()
