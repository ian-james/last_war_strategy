#!/usr/bin/env python3
"""
Verification script for Last War Scheduler refactoring.
Tests that all modules import correctly and key functions work.
"""

import sys
import os

# Add src to path
sys.path.insert(0, 'src')

def test_imports():
    """Test that all modules can be imported."""
    print("=" * 60)
    print("TESTING MODULE IMPORTS")
    print("=" * 60)

    tests = [
        ("Config constants", "from app.config import constants"),
        ("Config __init__", "from app.config import OVERLAP_MAP, SECRETARIES, SLOT_START_HOURS"),
        ("Utils helpers", "from app.utils import helpers"),
        ("Utils data_loaders", "from app.utils import data_loaders"),
        ("Utils task_manager", "from app.utils import task_manager"),
        ("Utils secretary", "from app.utils import secretary"),
        ("Utils time_utils", "from app.utils import time_utils"),
        ("Utils __init__", "from app.utils import word_in_text, format_duration"),
        ("Pages dashboard", "from app.pages import dashboard"),
        ("Pages weekly_calendar", "from app.pages import weekly_calendar"),
        ("Pages arms_scheduler", "from app.pages import arms_scheduler"),
        ("Pages vs_duel", "from app.pages import vs_duel"),
        ("Pages special_events", "from app.pages import special_events"),
        ("Pages daily_tasks", "from app.pages import daily_tasks"),
        ("Pages calculator", "from app.pages import calculator"),
        ("Pages secretary_buffs", "from app.pages import secretary_buffs"),
    ]

    passed = 0
    failed = 0

    for test_name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"✓ {test_name}")
            passed += 1
        except Exception as e:
            print(f"✗ {test_name}: {e}")
            failed += 1

    print(f"\nImport Tests: {passed} passed, {failed} failed")
    return failed == 0

def test_constants():
    """Test that constants are correctly defined."""
    print("\n" + "=" * 60)
    print("TESTING CONSTANTS")
    print("=" * 60)

    from app.config.constants import (
        SLOT_START_HOURS,
        OVERLAP_MAP,
        SECRETARIES,
        ARMS_RACE_FILE,
        VS_DUEL_FILE,
    )

    tests = [
        ("SLOT_START_HOURS", SLOT_START_HOURS == [0, 4, 8, 12, 16, 20]),
        ("OVERLAP_MAP keys", len(OVERLAP_MAP) == 6),
        ("SECRETARIES count", len(SECRETARIES) == 5),
        ("ARMS_RACE_FILE", ARMS_RACE_FILE == "data/arms_race_schedule.csv"),
        ("VS_DUEL_FILE", VS_DUEL_FILE == "data/vs_duel_schedule.csv"),
    ]

    passed = 0
    failed = 0

    for test_name, condition in tests:
        if condition:
            print(f"✓ {test_name}")
            passed += 1
        else:
            print(f"✗ {test_name}")
            failed += 1

    print(f"\nConstant Tests: {passed} passed, {failed} failed")
    return failed == 0

def test_functions():
    """Test that key functions work correctly."""
    print("\n" + "=" * 60)
    print("TESTING FUNCTIONS")
    print("=" * 60)

    from app.utils.helpers import format_duration, word_in_text

    tests = [
        ("format_duration(0)", format_duration(0) == "0m"),
        ("format_duration(45)", format_duration(45) == "45m"),
        ("format_duration(90)", format_duration(90) == "1h 30m"),
        ("format_duration(60)", format_duration(60) == "1h"),
        ("format_duration(1440)", format_duration(1440) == "1d"),
        ("format_duration(1530)", format_duration(1530) == "1d 1h"),
        ("word_in_text('test', 'this is a test')", word_in_text('test', 'this is a test')),
        ("word_in_text('TEST', 'this is a test')", word_in_text('TEST', 'this is a test')),
        ("not word_in_text('test', 'testing')", not word_in_text('test', 'testing')),
    ]

    passed = 0
    failed = 0

    for test_name, condition in tests:
        if condition:
            print(f"✓ {test_name}")
            passed += 1
        else:
            print(f"✗ {test_name}")
            failed += 1

    print(f"\nFunction Tests: {passed} passed, {failed} failed")
    return failed == 0

def test_file_structure():
    """Test that expected files exist."""
    print("\n" + "=" * 60)
    print("TESTING FILE STRUCTURE")
    print("=" * 60)

    expected_files = [
        "src/app/__init__.py",
        "src/app/main.py",
        "src/app/main_original_backup.py",
        "src/app/config/__init__.py",
        "src/app/config/constants.py",
        "src/app/utils/__init__.py",
        "src/app/utils/helpers.py",
        "src/app/utils/data_loaders.py",
        "src/app/utils/task_manager.py",
        "src/app/utils/secretary.py",
        "src/app/utils/time_utils.py",
        "src/app/pages/__init__.py",
        "src/app/pages/dashboard.py",
        "src/app/pages/weekly_calendar.py",
        "src/app/pages/arms_scheduler.py",
        "src/app/pages/vs_duel.py",
        "src/app/pages/special_events.py",
        "src/app/pages/daily_tasks.py",
        "src/app/pages/calculator.py",
        "src/app/pages/secretary_buffs.py",
        "src/app/components/__init__.py",
    ]

    passed = 0
    failed = 0

    for filepath in expected_files:
        if os.path.exists(filepath):
            print(f"✓ {filepath}")
            passed += 1
        else:
            print(f"✗ {filepath}")
            failed += 1

    print(f"\nFile Tests: {passed} passed, {failed} failed")
    return failed == 0

def test_line_counts():
    """Test that line counts match expectations."""
    print("\n" + "=" * 60)
    print("TESTING LINE COUNTS")
    print("=" * 60)

    def count_lines(filepath):
        with open(filepath, 'r') as f:
            return len(f.readlines())

    main_lines = count_lines('src/app/main.py')
    original_lines = count_lines('src/app/main_original_backup.py')

    tests = [
        ("main.py < 110 lines", main_lines < 110),
        ("main.py > 50 lines", main_lines > 50),
        ("original backup > 2000 lines", original_lines > 2000),
        ("main.py reduced by > 90%", main_lines < original_lines * 0.1),
    ]

    passed = 0
    failed = 0

    for test_name, condition in tests:
        if condition:
            print(f"✓ {test_name} (main={main_lines}, original={original_lines})")
            passed += 1
        else:
            print(f"✗ {test_name} (main={main_lines}, original={original_lines})")
            failed += 1

    print(f"\nLine Count Tests: {passed} passed, {failed} failed")
    return failed == 0

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("LAST WAR SCHEDULER REFACTORING VERIFICATION")
    print("=" * 60 + "\n")

    all_passed = True

    all_passed &= test_file_structure()
    all_passed &= test_imports()
    all_passed &= test_constants()
    all_passed &= test_functions()
    all_passed &= test_line_counts()

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nRefactoring verification successful!")
        print("The modular architecture is working correctly.\n")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        print("\nPlease review the failures above.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
