#!/usr/bin/env python3
"""
Test script to verify slot calculations are correct
"""

def calculate_slot_and_day(hour, day_name):
    """
    Calculate game day and slot for a given UTC hour
    Slot 1: 22:00-02:00
    Slot 2: 02:00-06:00
    Slot 3: 06:00-10:00
    Slot 4: 10:00-14:00
    Slot 5: 14:00-18:00
    Slot 6: 18:00-22:00
    """
    # Calculate game day
    if hour >= 22:
        game_day = "Next day"
    else:
        game_day = day_name

    # Calculate slot
    slot = ((hour - 22) % 24 // 4) + 1

    return game_day, slot

print("=" * 70)
print("Slot Calculation Test")
print("=" * 70)
print("\nExpected Mapping (for 'Monday'):")
print("  22:00 Mon - 01:59 Tue → Tuesday Slot 1")
print("  02:00 Tue - 05:59 Tue → Tuesday Slot 2")
print("  06:00 Tue - 09:59 Tue → Tuesday Slot 3")
print("  10:00 Tue - 13:59 Tue → Tuesday Slot 4")
print("  14:00 Tue - 17:59 Tue → Tuesday Slot 5")
print("  18:00 Tue - 21:59 Tue → Tuesday Slot 6")

print("\n" + "=" * 70)
print("Testing Key Hours:")
print("=" * 70)

test_cases = [
    (22, "Monday", "Tuesday", 1, "Start of Slot 1"),
    (23, "Monday", "Tuesday", 1, "Middle of Slot 1"),
    (0, "Tuesday", "Tuesday", 1, "Middle of Slot 1"),
    (1, "Tuesday", "Tuesday", 1, "End of Slot 1"),
    (2, "Tuesday", "Tuesday", 2, "Start of Slot 2"),
    (5, "Tuesday", "Tuesday", 2, "End of Slot 2"),
    (6, "Tuesday", "Tuesday", 3, "Start of Slot 3"),
    (9, "Tuesday", "Tuesday", 3, "End of Slot 3"),
    (10, "Tuesday", "Tuesday", 4, "Start of Slot 4"),
    (13, "Tuesday", "Tuesday", 4, "End of Slot 4"),
    (14, "Tuesday", "Tuesday", 5, "Start of Slot 5"),
    (17, "Tuesday", "Tuesday", 5, "End of Slot 5"),
    (18, "Tuesday", "Tuesday", 6, "Start of Slot 6"),
    (21, "Tuesday", "Tuesday", 6, "End of Slot 6"),
]

all_passed = True
for hour, calendar_day, expected_game_day, expected_slot, description in test_cases:
    calc_day, calc_slot = calculate_slot_and_day(hour, calendar_day)

    # Adjust for display
    if calc_day == "Next day":
        display_day = expected_game_day
    else:
        display_day = calendar_day

    passed = (calc_slot == expected_slot)
    status = "✅" if passed else "❌"

    print(f"\n{status} Hour {hour:02d}:00 on {calendar_day} - {description}")
    print(f"   Expected: {expected_game_day} Slot {expected_slot}")
    print(f"   Calculated: {display_day} Slot {calc_slot}")

    if not passed:
        all_passed = False
        print(f"   ERROR: Expected Slot {expected_slot}, got Slot {calc_slot}")

print("\n" + "=" * 70)
if all_passed:
    print("✅ All tests PASSED!")
else:
    print("❌ Some tests FAILED - review calculations")
print("=" * 70)

# Test the formula directly
print("\n" + "=" * 70)
print("Formula Test: ((hour - 22) % 24 // 4) + 1")
print("=" * 70)
for h in range(24):
    slot = ((h - 22) % 24 // 4) + 1
    print(f"Hour {h:02d}: Slot {slot}")
