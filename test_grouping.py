#!/usr/bin/env python3
"""Test the task grouping function."""


def group_tasks_by_base_name(task_names: list) -> list:
    """Group tasks with the same base name and combine their rarity suffixes.

    Example:
        ["Secret Mobile Squad (UR)", "Secret Mobile Squad (SSR)", "Other Task"]
        → ["Secret Mobile Squad (UR, SSR)", "Other Task"]

    Args:
        task_names: List of task name strings

    Returns:
        List of grouped task names
    """
    if not task_names:
        return []

    # Dictionary to group tasks: {base_name: [suffix1, suffix2, ...]}
    grouped = {}

    for task in task_names:
        # Check if task has a rarity suffix in parentheses at the end
        if '(' in task and task.endswith(')'):
            # Split at the last opening parenthesis
            last_paren = task.rfind('(')
            base_name = task[:last_paren].strip()
            suffix = task[last_paren+1:-1].strip()  # Remove '(' and ')'

            if base_name not in grouped:
                grouped[base_name] = []
            grouped[base_name].append(suffix)
        else:
            # Task without rarity suffix, add as-is
            if task not in grouped:
                grouped[task] = []

    # Reconstruct grouped task names
    result = []
    for base_name, suffixes in grouped.items():
        if suffixes:
            # Combine suffixes: "Base Name (S1, S2, S3)"
            combined_suffix = ", ".join(suffixes)
            result.append(f"{base_name} ({combined_suffix})")
        else:
            # No suffix, just the base name
            result.append(base_name)

    return result


def test_grouping():
    """Test various grouping scenarios."""

    # Test 1: Group tasks with same base name
    tasks1 = ["Secret Mobile Squad (UR)", "Secret Mobile Squad (SSR)", "Other Task"]
    result1 = group_tasks_by_base_name(tasks1)
    print(f"Test 1: {tasks1}")
    print(f"Result: {result1}")
    print(f"Expected: ['Secret Mobile Squad (UR, SSR)', 'Other Task']")
    print()

    # Test 2: Tasks with multiple rarities
    tasks2 = ["Gathering (N)", "Gathering (R)", "Gathering (SR)", "Combat (UR)"]
    result2 = group_tasks_by_base_name(tasks2)
    print(f"Test 2: {tasks2}")
    print(f"Result: {result2}")
    print(f"Expected: ['Gathering (N, R, SR)', 'Combat (UR)']")
    print()

    # Test 3: Tasks without rarity suffixes
    tasks3 = ["Simple Task", "Another Task"]
    result3 = group_tasks_by_base_name(tasks3)
    print(f"Test 3: {tasks3}")
    print(f"Result: {result3}")
    print(f"Expected: ['Simple Task', 'Another Task']")
    print()

    # Test 4: Mixed tasks (some with, some without suffixes)
    tasks4 = ["Build Tower (SR)", "Build Tower (UR)", "Research"]
    result4 = group_tasks_by_base_name(tasks4)
    print(f"Test 4: {tasks4}")
    print(f"Result: {result4}")
    print(f"Expected: ['Build Tower (SR, UR)', 'Research']")
    print()

    # Test 5: Empty list
    tasks5 = []
    result5 = group_tasks_by_base_name(tasks5)
    print(f"Test 5: {tasks5}")
    print(f"Result: {result5}")
    print(f"Expected: []")
    print()

    # Test 6: Single task
    tasks6 = ["Lone Task (SSR)"]
    result6 = group_tasks_by_base_name(tasks6)
    print(f"Test 6: {tasks6}")
    print(f"Result: {result6}")
    print(f"Expected: ['Lone Task (SSR)']")
    print()


if __name__ == "__main__":
    test_grouping()
