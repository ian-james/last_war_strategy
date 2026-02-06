"""Speed-Up Calculator page."""

import streamlit as st
from app.utils.helpers import format_duration


def render(time_ctx: dict):
    """Render the Speed-Up Calculator page.

    Args:
        time_ctx: Dictionary from setup_timezone_and_time() (not used but kept for consistency)
    """
    st.title("⏩ Speed-Up Calculator")
    st.caption("Enter a base activity duration and add speed-up items to see how much time remains.")

    # --- Base Activity card ---
    with st.container(border=True):
        st.subheader("Base Activity")
        su_activity_type = st.selectbox(
            "Activity Type",
            ["Training", "Research", "Construction", "Other"],
            key="su_activity_type"
        )
        dur_cols = st.columns(3)
        su_days = dur_cols[0].number_input("Days", min_value=0, value=0, step=1, key="su_base_days")
        su_hours = dur_cols[1].number_input("Hours", min_value=0, value=0, step=1, key="su_base_hours")
        su_mins = dur_cols[2].number_input("Minutes", min_value=0, value=0, step=1, key="su_base_mins")

    base_total_minutes = su_days * 1440 + su_hours * 60 + su_mins

    # Denominations available in the game (shared by both pools)
    su_denoms = [
        ("8 Hours", 480),
        ("1 Hour", 60),
        ("15 Min", 15),
        ("5 Min", 5),
        ("1 Min", 1),
    ]

    # --- General Speed-Ups card ---
    with st.container(border=True):
        st.subheader("General Speed-Ups")
        gen_cols = st.columns(5)
        gen_quantities = []
        for i, (label, _) in enumerate(su_denoms):
            qty = gen_cols[i].number_input(label, min_value=0, value=0, step=1, key=f"su_gen_qty_{i}")
            gen_quantities.append(qty)

    # --- Typed Speed-Ups card (type is driven by Base Activity) ---
    with st.container(border=True):
        st.subheader(f"{su_activity_type} Speed-Ups")
        typ_cols = st.columns(5)
        typ_quantities = []
        for i, (label, _) in enumerate(su_denoms):
            qty = typ_cols[i].number_input(label, min_value=0, value=0, step=1, key=f"su_typ_qty_{i}")
            typ_quantities.append(qty)

    # --- Calculations ---
    gen_total = sum(qty * mins for qty, (_, mins) in zip(gen_quantities, su_denoms))
    typ_total = sum(qty * mins for qty, (_, mins) in zip(typ_quantities, su_denoms))
    speedup_total_minutes = gen_total + typ_total
    remaining_minutes = max(base_total_minutes - speedup_total_minutes, 0)
    leftover_minutes = max(speedup_total_minutes - base_total_minutes, 0)
    pct_covered = (speedup_total_minutes / base_total_minutes * 100) if base_total_minutes > 0 else 0

    # How much of each pool actually gets used (typed first, general fills the rest)
    typed_applied = min(typ_total, base_total_minutes)
    general_applied = min(gen_total, max(base_total_minutes - typ_total, 0))

    # --- Results ---
    st.divider()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Base Duration", format_duration(base_total_minutes))
    m2.metric(f"{su_activity_type} Used", format_duration(typed_applied))
    m3.metric("General Used", format_duration(general_applied))
    m4.metric("Time Remaining", format_duration(remaining_minutes))

    # --- Progress bar + status ---
    if base_total_minutes == 0:
        st.warning("Enter a base duration above to start calculating.")
    else:
        # Color thresholds: red < 50 %, amber 50–99 %, green >= 100 %
        if pct_covered >= 100:
            bar_color = "#28a745"
        elif pct_covered >= 50:
            bar_color = "#ffc107"
        else:
            bar_color = "#dc3545"

        bar_width = min(pct_covered, 100)
        st.html(f"""
            <div style="width:100%; background:#e9ecef; border-radius:8px; height:28px; overflow:hidden;">
              <div style="width:{bar_width}%; background:{bar_color}; height:100%; border-radius:8px;
                         transition:width 0.3s ease; display:flex; align-items:center; padding-left:10px;">
                <span style="color:#fff; font-weight:bold; font-size:14px;">{pct_covered:.0f}%</span>
              </div>
            </div>
        """)

        if pct_covered >= 100:
            st.success(f"Fully covered! {format_duration(leftover_minutes)} left over.")
        else:
            st.warning(f"Still needs {format_duration(remaining_minutes)} of speed-ups.")

    # --- Speed-Ups Still Needed (greedy breakdown of remaining time) ---
    if remaining_minutes > 0:
        st.divider()
        st.subheader("Speed-Ups Still Needed")
        st.caption("Minimum items to cover the remaining time (largest first):")
        needed_cols = st.columns(5)
        rem = remaining_minutes
        for i, (label, val) in enumerate(su_denoms):
            count = int(rem // val)
            rem -= count * val
            needed_cols[i].metric(label, str(count) if count else "—")
