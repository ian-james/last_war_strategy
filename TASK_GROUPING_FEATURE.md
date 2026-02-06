# Task Grouping Feature

## Overview
Implemented task grouping in the Dashboard's 24-Hour Optimization table to combine duplicate daily tasks with different rarity levels into a single display entry.

## Feature Description
When multiple active daily tasks have the same base name but different rarity suffixes (e.g., N, R, SR, SSR, UR), they are now grouped together in the dashboard display:

**Before:**
- Secret Mobile Squad (UR)
- Secret Mobile Squad (SSR)
- Other Task

**After:**
- Secret Mobile Squad (UR, SSR)
- Other Task

## Implementation Details

### New Function: `group_tasks_by_base_name()`
**Location:** `src/app/pages/dashboard.py`

```python
def group_tasks_by_base_name(task_names: list) -> list:
    """Group tasks with the same base name and combine their rarity suffixes.

    Example:
        ["Secret Mobile Squad (UR)", "Secret Mobile Squad (SSR)", "Other Task"]
        → ["Secret Mobile Squad (UR, SSR)", "Other Task"]
    """
```

**Algorithm:**
1. Parse each task name to extract the base name (everything before the last `(`)
2. Extract the rarity suffix (e.g., UR, SSR, SR, R, N)
3. Group tasks by base name
4. Combine suffixes with commas: `"Base Name (S1, S2, S3)"`
5. Preserve tasks without rarity suffixes as-is

### Integration Points
**Modified location:** `src/app/pages/dashboard.py:583-588`

```python
# Get active daily tasks in this window
window_end = b_srv.add(hours=4)
active_daily_tasks = get_active_tasks_in_window(b_srv, window_end)
# Group tasks with the same base name (e.g., "Secret Mobile Squad (UR, SSR)")
grouped_tasks = group_tasks_by_base_name(active_daily_tasks)
daily_tasks_str = ", ".join(grouped_tasks) if grouped_tasks else ""
```

## Scope
**Where grouping applies:**
- ✅ Dashboard → 24-Hour Optimization table
- ✅ Dashboard → Optimization table detailed view
- ✅ Dashboard → Daily Tasks column display

**Where grouping does NOT apply:**
- ❌ Daily Tasks Manager page (tasks remain separate for individual activation)
- ❌ Active tasks data structure (stored separately in CSV)
- ❌ Task activation/completion tracking

## User Experience
### Dashboard View
Users will see a cleaner, more concise display in the optimization table:
- Fewer lines to scan
- Clearer understanding of which tasks are active
- All rarity levels visible at a glance

### Daily Tasks Manager
Users can still activate tasks individually by rarity level:
- Each rarity remains a separate activation button
- Activation limits tracked per task name (not per rarity)
- No changes to activation workflow

## Testing
Created comprehensive test suite in `test_grouping.py`:

**Test Coverage:**
1. ✅ Group tasks with same base name
2. ✅ Multiple rarities (N, R, SR, SSR, UR)
3. ✅ Tasks without rarity suffixes
4. ✅ Mixed tasks (some with, some without suffixes)
5. ✅ Empty list handling
6. ✅ Single task handling

**Run tests:**
```bash
python test_grouping.py
```

All tests pass successfully.

## Edge Cases Handled
1. **Tasks without parentheses:** Displayed as-is (e.g., "Research")
2. **Tasks with non-rarity parentheses:** Treated as suffix (e.g., "Build (Fast)" → "Build (Fast)")
3. **Empty task list:** Returns empty list
4. **Single task:** Returns unchanged (e.g., "Task (UR)" → "Task (UR)")
5. **Tasks with same base but no suffix:** Grouped together (e.g., ["Task", "Task"] → ["Task"])

## Files Modified
- `src/app/pages/dashboard.py` (+50 lines)
  - Added `group_tasks_by_base_name()` function
  - Applied grouping to daily tasks display

- `test_grouping.py` (+109 lines, new file)
  - Comprehensive test suite

## Performance Impact
- **Minimal:** O(n) complexity where n = number of active tasks in a 4-hour window
- **Typical usage:** 0-5 active tasks per window
- **No database or file I/O added**

## Future Enhancements
Potential improvements (not implemented):
1. Custom grouping rules per task type
2. Sort suffixes by rarity order (N, R, SR, SSR, UR)
3. Color-code grouped tasks by highest rarity
4. Add group/ungroup toggle in UI
5. Apply grouping to other views (Weekly Calendar, Special Events)

## Commit
```
commit 63a378c
Author: James <jame@localhost>
Date:   Thu Feb 6 08:05:31 2026 -0400

    Group duplicate daily tasks in Dashboard's 24-Hour Optimization table.
```

## User Feedback
> "Sorry, I want them separate on the daily task manager page but on the dashboard when active in the 24 Hour Optimization table I want them grouped together"

✅ **Implemented as requested**
