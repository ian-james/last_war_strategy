"""Helper utility functions."""

import re
import pendulum


def word_in_text(keyword, text):
    """Check if keyword appears as a whole word in text (case-insensitive)"""
    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
    return bool(re.search(pattern, text.lower()))


def format_duration(total_minutes):
    """Format minutes into a compact string: '2d 4h', '1h 30m', '45m', or '0m'."""
    if total_minutes <= 0:
        return "0m"
    days = int(total_minutes // 1440)
    hours = int((total_minutes % 1440) // 60)
    mins = int(total_minutes % 60)
    if days:
        return f"{days}d {hours}h" if hours else f"{days}d"
    if hours:
        return f"{hours}h {mins}m" if mins else f"{hours}h"
    return f"{mins}m"


def is_event_in_window(event_row, window_start):
    """Check if a special event overlaps a 4-hour window.

    Args:
        event_row: DataFrame row with columns: days, freq, ref_week, start_time, end_time
        window_start: pendulum DateTime (server time). Event times in the CSV are
                     assumed to be in the same frame as window_start.

    Returns:
        bool: True if the event overlaps the 4-hour window starting at window_start
    """
    days = str(event_row['days']).split(',')
    if window_start.format('dddd') not in days:
        return False

    if event_row['freq'] == 'biweekly':
        if (window_start.week_of_year % 2) != (int(event_row['ref_week']) % 2):
            return False

    # Build absolute datetimes on the window's calendar date
    base = window_start.start_of('day')
    sh, sm = map(int, str(event_row['start_time']).split(':'))
    eh, em = map(int, str(event_row['end_time']).split(':'))
    evt_start = base.set(hour=sh, minute=sm)
    evt_end = base.set(hour=eh, minute=em)

    # end ≤ start means the event wraps past midnight → end is next day
    if evt_end <= evt_start:
        evt_end = evt_end.add(days=1)

    win_start = window_start
    win_end = window_start.add(hours=4)

    # Standard interval-overlap check (works across midnight automatically)
    return evt_start < win_end and evt_end > win_start
