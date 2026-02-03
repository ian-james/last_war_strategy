#!/usr/bin/env python3
"""
Test script to verify active slot and window start calculations
"""
from datetime import datetime, timedelta

def calculate_current_slot_and_window(hour, day_of_week):
    """Calculate current slot and window start time"""
    # Calculate current slot using new timing (Slot 1 starts at 22:00)
    current_slot = ((hour - 22) % 24 // 4) + 1

    # Map slots to their start hours
    slot_start_hours = [22, 2, 6, 10, 14, 18]
    start_hour = slot_start_hours[current_slot - 1]

    # Calculate game day
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    current_day_idx = days.index(day_of_week)

    if hour >= 22:
        game_day_idx = (current_day_idx + 1) % 7
        game_day = days[game_day_idx]
    else:
        game_day = day_of_week

    return current_slot, start_hour, game_day

print("=" * 80)
print("Current Slot and Window Start Calculation Test")
print("=" * 80)

# Test cases: (hour, calendar_day, expected_slot, expected_start_hour, expected_game_day, description)
test_cases = [
    (22, "Monday", 1, 22, "Tuesday", "Mon 22:00 = Tue Slot 1"),
    (23, "Monday", 1, 22, "Tuesday", "Mon 23:30 = Tue Slot 1"),
    (0, "Tuesday", 1, 22, "Tuesday", "Tue 00:30 = Tue Slot 1 (window started Mon 22:00)"),
    (1, "Tuesday", 1, 22, "Tuesday", "Tue 01:30 = Tue Slot 1 (window started Mon 22:00)"),
    (2, "Tuesday", 2, 2, "Tuesday", "Tue 02:00 = Tue Slot 2"),
    (5, "Tuesday", 2, 2, "Tuesday", "Tue 05:30 = Tue Slot 2"),
    (6, "Tuesday", 3, 6, "Tuesday", "Tue 06:00 = Tue Slot 3"),
    (10, "Tuesday", 4, 10, "Tuesday", "Tue 10:00 = Tue Slot 4"),
    (14, "Tuesday", 5, 14, "Tuesday", "Tue 14:00 = Tue Slot 5"),
    (18, "Tuesday", 6, 18, "Tuesday", "Tue 18:00 = Tue Slot 6"),
    (21, "Tuesday", 6, 18, "Tuesday", "Tue 21:30 = Tue Slot 6"),
]

all_passed = True
for hour, cal_day, exp_slot, exp_start_hr, exp_game_day, description in test_cases:
    calc_slot, calc_start_hr, calc_game_day = calculate_current_slot_and_window(hour, cal_day)

    slot_match = (calc_slot == exp_slot)
    start_match = (calc_start_hr == exp_start_hr)
    day_match = (calc_game_day == exp_game_day)

    all_match = slot_match and start_match and day_match
    status = "✅" if all_match else "❌"

    print(f"\n{status} {description}")
    print(f"   Expected: {exp_game_day} Slot {exp_slot}, window starts hour {exp_start_hr}")
    print(f"   Calculated: {calc_game_day} Slot {calc_slot}, window starts hour {calc_start_hr}")

    if not all_match:
        all_passed = False
        if not slot_match:
            print(f"   ❌ SLOT ERROR: Expected {exp_slot}, got {calc_slot}")
        if not start_match:
            print(f"   ❌ START ERROR: Expected hour {exp_start_hr}, got hour {calc_start_hr}")
        if not day_match:
            print(f"   ❌ DAY ERROR: Expected {exp_game_day}, got {calc_game_day}")

print("\n" + "=" * 80)
if all_passed:
    print("✅ All tests PASSED! The slot calculation is correct.")
else:
    print("❌ Some tests FAILED")
print("=" * 80)
