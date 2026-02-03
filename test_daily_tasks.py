#!/usr/bin/env python3
"""
Quick verification script for Daily Tasks feature
Run this to verify the implementation without starting Streamlit
"""

import os
import sys

def verify_files():
    """Verify all required files exist"""
    files = {
        'Templates': 'data/daily_task_templates.csv',
        'Active Tasks': 'data/active_daily_tasks.csv',
        'Restore Defaults': 'data/restore_daily_task_templates.csv',
        'Main App': 'src/app/main.py'
    }

    print("📁 File Verification:")
    all_exist = True
    for name, path in files.items():
        exists = os.path.exists(path)
        status = "✅" if exists else "❌"
        print(f"  {status} {name}: {path}")
        all_exist = all_exist and exists

    return all_exist

def verify_code_structure():
    """Verify code contains required components"""
    print("\n🔍 Code Structure Verification:")

    with open('src/app/main.py', 'r') as f:
        content = f.read()

    checks = {
        'Constants defined': all([
            'DAILY_TEMPLATES_FILE' in content,
            'ACTIVE_TASKS_FILE' in content,
            'RESTORE_TEMPLATES_FILE' in content
        ]),
        'Helper functions': all([
            'def get_daily_templates()' in content,
            'def get_active_tasks()' in content,
            'def cleanup_expired_tasks()' in content,
            'def get_active_tasks_in_window(' in content
        ]),
        'Navigation updated': '"Daily Tasks Manager"' in content,
        'Dashboard integration': '"Daily Tasks": daily_tasks_str' in content,
        'Page implementation': 'elif page == "Daily Tasks Manager":' in content,
        'Auto-cleanup call': 'cleanup_expired_tasks()' in content,
        'Daily counter function': 'def get_daily_activation_count' in content,
        'Icon selector': 'icon_options' in content
    }

    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        all_passed = all_passed and passed

    return all_passed

def verify_csv_structure():
    """Verify CSV files have correct headers"""
    print("\n📊 CSV Structure Verification:")

    csv_checks = {
        'Templates': {
            'file': 'data/daily_task_templates.csv',
            'expected': ['name', 'duration_n', 'duration_r', 'duration_sr', 'duration_ssr', 'duration_ur', 'max_daily', 'category', 'color_code', 'icon', 'is_default']
        },
        'Active Tasks': {
            'file': 'data/active_daily_tasks.csv',
            'expected': ['task_id', 'task_name', 'start_time_utc', 'duration_minutes', 'end_time_utc', 'status']
        }
    }

    all_valid = True
    for name, config in csv_checks.items():
        with open(config['file'], 'r') as f:
            header = f.readline().strip().split('\t')

        valid = header == config['expected']
        status = "✅" if valid else "❌"
        print(f"  {status} {name} CSV headers")
        if not valid:
            print(f"      Expected: {config['expected']}")
            print(f"      Got: {header}")
        all_valid = all_valid and valid

    return all_valid

def count_default_tasks():
    """Count default tasks in templates"""
    print("\n📋 Default Tasks with Rarity Level Durations:")

    with open('data/daily_task_templates.csv', 'r') as f:
        lines = f.readlines()

    # Parse header to get column indices
    header = lines[0].strip().split('\t')
    name_idx = header.index('name')
    n_idx = header.index('duration_n')
    r_idx = header.index('duration_r')
    sr_idx = header.index('duration_sr')
    ssr_idx = header.index('duration_ssr')
    ur_idx = header.index('duration_ur')
    max_daily_idx = header.index('max_daily')

    tasks = []
    for line in lines[1:]:  # Skip header
        if line.strip():
            parts = line.split('\t')
            name = parts[name_idx]
            dur_n = parts[n_idx]
            dur_r = parts[r_idx]
            dur_sr = parts[sr_idx]
            dur_ssr = parts[ssr_idx]
            dur_ur = parts[ur_idx]
            max_daily = parts[max_daily_idx]

            # Check if has level variants
            if dur_n == dur_r == dur_sr == dur_ssr == dur_ur:
                print(f"  • {name}: {dur_n}m (no variants) | Max: {max_daily}/day")
            else:
                print(f"  • {name}: N={dur_n}m, R={dur_r}m, SR={dur_sr}m, SSR={dur_ssr}m, UR={dur_ur}m | Max: {max_daily}/day")

            tasks.append(name)

    return len(tasks)

def main():
    print("=" * 60)
    print("Daily Tasks Feature - Verification Report")
    print("=" * 60)

    files_ok = verify_files()
    code_ok = verify_code_structure()
    csv_ok = verify_csv_structure()
    task_count = count_default_tasks()

    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print(f"  Files: {'✅ PASS' if files_ok else '❌ FAIL'}")
    print(f"  Code Structure: {'✅ PASS' if code_ok else '❌ FAIL'}")
    print(f"  CSV Structure: {'✅ PASS' if csv_ok else '❌ FAIL'}")
    print(f"  Default Tasks: {task_count} templates loaded")

    all_passed = files_ok and code_ok and csv_ok
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All verifications passed! Feature ready to use.")
        print("\nTo test the app, run:")
        print("  streamlit run src/app/main.py")
    else:
        print("⚠️  Some verifications failed. Please review above.")
        sys.exit(1)
    print("=" * 60)

if __name__ == "__main__":
    main()
