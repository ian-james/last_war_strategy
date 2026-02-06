# Tactical Slot Swap Feature

## Overview

The Tactical Slot Swap feature allows players to swap the current time slot with another slot **once per day** for **today only**. This is useful when you realize mid-slot that you need to do a different activity but want to preserve your overall weekly rotation.

## Key Features

✅ **One swap per day** - Can only be used once until daily reset
✅ **Current slot only** - Must swap from the current time slot
✅ **Today only** - Does not affect your long-term weekly schedule
✅ **Automatic reset** - Resets at 02:00 server time (daily reset)
✅ **Cancellable** - Can cancel an active swap to restore normal schedule
✅ **Visible status** - Shows active swap and when it resets

## How It Works

### Daily Reset
- Swap availability resets at **02:00 server time** (game's daily reset)
- The swap remains active until the next 02:00 reset
- After reset, you can swap again (if needed)

### Swap Process
1. Navigate to **Strategic Dashboard**
2. Find the "🔄 Tactical Slot Swap" section (above 24-Hour Optimization Plan)
3. Expand the section if it's collapsed
4. Select which slot to swap with from the dropdown
5. Click "🔄 Swap Slots"
6. The schedule updates immediately and shows throughout the app

### What Gets Swapped
- **Arms Race events only** - VS Duel events are not affected
- **All tasks in the slot** - If a slot has multiple tasks, all are swapped
- **Display everywhere** - The swap applies to Dashboard, Optimization Plan, etc.

## Use Cases

### Example 1: Wrong Priority
- **Current Slot 3 (06:00-10:00):** Hero Development
- **Slot 5 (14:00-18:00):** Base Building
- **Problem:** You just realized you need to focus on base building now
- **Solution:** Swap Slot 3 ↔ Slot 5 for today

### Example 2: Emergency Event
- **Current Slot 2 (02:00-06:00):** Tech Research
- **Slot 4 (10:00-14:00):** Unit Progression
- **Problem:** Alliance is under attack, need to train units NOW
- **Solution:** Swap Slot 2 ↔ Slot 4 for today

### Example 3: Resource Timing
- **Current Slot 6 (18:00-22:00):** All-Rounder
- **Slot 1 (22:00-02:00):** Drone Boost
- **Problem:** Drone parts expire soon, need to use them now
- **Solution:** Swap Slot 6 ↔ Slot 1 for today

## Technical Implementation

### File Structure
```
src/app/utils/slot_swap.py      # Slot swap management logic
data/daily_slot_swap.json       # Stores active swap (if any)
```

### Data Storage
```json
{
  "date": "2026-02-05",
  "from_slot": 3,
  "to_slot": 5
}
```

### Functions

**get_daily_slot_swap()** - Retrieve active swap
```python
swap = get_daily_slot_swap()
# Returns: {"date": "...", "from_slot": 3, "to_slot": 5} or None
```

**save_daily_slot_swap(from_slot, to_slot, game_date)** - Create new swap
```python
save_daily_slot_swap(3, 5, "2026-02-05")
```

**can_swap_today(now_server)** - Check if swap is available
```python
if can_swap_today(now_server):
    # User can swap
```

**apply_slot_swap(df, day, now_server)** - Apply swap to schedule
```python
df = apply_slot_swap(df, "Thursday", now_server)
# Returns modified DataFrame with swapped slots
```

**clear_daily_slot_swap()** - Cancel active swap
```python
clear_daily_slot_swap()
```

## UI Location

The Tactical Slot Swap UI is located on the **Strategic Dashboard** page:

1. Scroll down past the Active Tasks section
2. Look for the "🔄 Tactical Slot Swap (Once Daily)" expander
3. If you've already swapped today, you'll see the status and a cancel button

## Limitations

❌ **Cannot swap past slots** - Can only swap from current slot
❌ **Cannot swap future slots** - Must be in the slot to swap it
❌ **One swap per day** - Used up until 02:00 reset tomorrow
❌ **Same day only** - Cannot swap slots from different days
❌ **Arms Race only** - Does not affect VS Duel schedule

## Automatic Cleanup

- **Expired swaps** are automatically detected and cleared
- **Date validation** ensures swaps don't carry over incorrectly
- **Daily reset** at 02:00 server time restores swap availability

## Integration Points

The swap is applied in multiple places:

1. **Dashboard** - Strategic Dashboard applies swap on load
2. **Optimization Plan** - 24-Hour table shows swapped schedule
3. **Current Events** - Displays correct event for swapped slot
4. **All calculations** - 2× detection, special events, etc. use swapped data

## Rollback

To manually clear an active swap:
```bash
rm data/daily_slot_swap.json
```

Or use the "❌ Cancel Swap" button in the UI.

## Future Enhancements

Possible improvements (not implemented):
- Swap multiple slots in sequence
- Preview swap before applying
- Swap history/analytics
- Auto-suggest optimal swaps based on active events

---

**Feature Added:** 2026-02-05
**Version:** 2.0.1
**Location:** `src/app/utils/slot_swap.py`, `src/app/pages/dashboard.py`
