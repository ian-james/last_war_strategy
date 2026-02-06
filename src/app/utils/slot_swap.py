"""Daily slot swap management for tactical Arms Race adjustments."""

import os
import json
import pandas as pd
import pendulum
from typing import Optional, Dict, Tuple


SLOT_SWAP_FILE = "data/daily_slot_swap.json"


def get_daily_slot_swap() -> Optional[Dict]:
    """Get the current daily slot swap if it exists and is still valid.

    Returns:
        Dict with keys: date, from_slot, to_slot, or None if no active swap
    """
    if not os.path.exists(SLOT_SWAP_FILE):
        return None

    try:
        with open(SLOT_SWAP_FILE, 'r') as f:
            swap_data = json.load(f)

        # Return None if no swap data
        if not swap_data or not swap_data.get('date'):
            return None

        return swap_data
    except (json.JSONDecodeError, IOError):
        return None


def is_swap_expired(swap_data: Dict, now_server: pendulum.DateTime) -> bool:
    """Check if a swap has expired (past the daily reset).

    Daily reset is at 02:00 server time. The swap is valid until the next reset.

    Args:
        swap_data: Swap data dictionary with 'date' key (YYYY-MM-DD)
        now_server: Current server time

    Returns:
        True if the swap has expired, False if still valid
    """
    if not swap_data or 'date' not in swap_data:
        return True

    # Parse the swap date
    swap_date_str = swap_data['date']
    try:
        swap_date = pendulum.parse(swap_date_str, tz='UTC')
    except:
        return True

    # Calculate the reset time for the swap date (02:00 server time)
    # The swap is valid from its date at 02:00 until the next day at 02:00
    swap_reset_start = swap_date.in_tz(now_server.timezone).set(hour=2, minute=0, second=0)
    swap_reset_end = swap_reset_start.add(days=1)

    # Check if current server time is past the expiration
    return now_server >= swap_reset_end


def save_daily_slot_swap(from_slot: int, to_slot: int, game_date: str) -> None:
    """Save a new daily slot swap.

    Args:
        from_slot: Source slot number (1-6)
        to_slot: Destination slot number (1-6)
        game_date: Game date string (YYYY-MM-DD in server timezone)
    """
    swap_data = {
        'date': game_date,
        'from_slot': from_slot,
        'to_slot': to_slot
    }

    with open(SLOT_SWAP_FILE, 'w') as f:
        json.dump(swap_data, f, indent=2)


def clear_daily_slot_swap() -> None:
    """Clear the current daily slot swap."""
    if os.path.exists(SLOT_SWAP_FILE):
        os.remove(SLOT_SWAP_FILE)


def can_swap_today(now_server: pendulum.DateTime) -> bool:
    """Check if a swap is available today.

    Args:
        now_server: Current server time

    Returns:
        True if user can swap today, False if already used
    """
    swap_data = get_daily_slot_swap()

    # No swap exists - can swap
    if not swap_data:
        return True

    # Swap exists but expired - can swap
    if is_swap_expired(swap_data, now_server):
        clear_daily_slot_swap()
        return True

    # Active swap exists - cannot swap again today
    return False


def apply_slot_swap(df: pd.DataFrame, day: str, now_server: pendulum.DateTime) -> pd.DataFrame:
    """Apply the daily slot swap to a dataframe if one exists for today.

    Args:
        df: DataFrame with Arms Race schedule
        day: Day name (e.g., "Thursday")
        now_server: Current server time

    Returns:
        Modified DataFrame with swap applied (if applicable)
    """
    swap_data = get_daily_slot_swap()

    # No swap or expired swap - return unchanged
    if not swap_data or is_swap_expired(swap_data, now_server):
        if swap_data:  # Clean up expired swap
            clear_daily_slot_swap()
        return df

    # Get swap parameters
    from_slot = swap_data['from_slot']
    to_slot = swap_data['to_slot']

    # Filter today's Arms Race events
    today_ar = df[(df['Day'] == day) & (df['Type'] == 'Arms Race')].copy()

    if today_ar.empty:
        return df

    # Swap the slot numbers using a temporary value to avoid collision
    # First, mark from_slot with a temporary value
    today_ar.loc[today_ar['Slot'] == from_slot, 'Slot'] = -1
    # Then, change to_slot to from_slot
    today_ar.loc[today_ar['Slot'] == to_slot, 'Slot'] = from_slot
    # Finally, change the temporary value to to_slot
    today_ar.loc[today_ar['Slot'] == -1, 'Slot'] = to_slot

    # Remove original today's data and add swapped data
    df_other = df[~((df['Day'] == day) & (df['Type'] == 'Arms Race'))]
    result = pd.concat([df_other, today_ar], ignore_index=True)

    return result
