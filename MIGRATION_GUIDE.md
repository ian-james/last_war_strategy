# Migration Guide: Monolithic to Modular Architecture

## Overview

This guide helps you understand the changes from the monolithic `main.py` (2010 lines) to the new modular architecture.

## What Changed?

### File Structure
**Before:**
```
src/app/
└── main.py (2010 lines)
```

**After:**
```
src/app/
├── main.py (94 lines)
├── config/
│   ├── constants.py
│   └── __init__.py
├── utils/
│   ├── helpers.py
│   ├── data_loaders.py
│   ├── task_manager.py
│   ├── secretary.py
│   ├── time_utils.py
│   └── __init__.py
└── pages/
    ├── dashboard.py
    ├── weekly_calendar.py
    ├── arms_scheduler.py
    ├── vs_duel.py
    ├── special_events.py
    ├── daily_tasks.py
    ├── calculator.py
    ├── secretary_buffs.py
    └── __init__.py
```

## Breaking Changes

**None!** The application maintains 100% functional compatibility.

## How to Use the New Structure

### Running the Application
No changes needed! Run the app the same way:
```bash
streamlit run src/app/main.py
```

### Accessing Constants
**Before:**
```python
# In main.py
OVERLAP_MAP = {...}
slot_start_hours = [0, 4, 8, 12, 16, 20]
```

**After:**
```python
from app.config.constants import OVERLAP_MAP, SLOT_START_HOURS
```

### Using Helper Functions
**Before:**
```python
# In main.py
def format_duration(total_minutes):
    # ...
```

**After:**
```python
from app.utils.helpers import format_duration
```

### Loading Data
**Before:**
```python
# In main.py
def get_game_data():
    # ...
```

**After:**
```python
from app.utils.data_loaders import get_game_data
```

### Time Setup
**Before:**
```python
# In main.py
# Inline sidebar setup
server_tz = ...
now_server = pendulum.now(server_tz)
current_slot = (now_server.hour // 4) + 1
# ... (many lines)
```

**After:**
```python
from app.utils.time_utils import setup_timezone_and_time

time_ctx = setup_timezone_and_time()
# Access values: time_ctx['now_server'], time_ctx['current_slot'], etc.
```

### Page Rendering
**Before:**
```python
# In main.py
if page == "Strategic Dashboard":
    st.title("Strategic Dashboard")
    # ... (hundreds of lines)
```

**After:**
```python
from app.pages import dashboard

if page == "Strategic Dashboard":
    dashboard.render(time_ctx, df, specials_df)
```

## Code Location Reference

### Constants
| Item | Before | After |
|------|--------|-------|
| File paths | `main.py` lines 10-17 | `config/constants.py` |
| OVERLAP_MAP | `main.py` lines 160-167 | `config/constants.py` |
| SECRETARIES | `main.py` lines 183-204 | `config/constants.py` |
| SLOT_START_HOURS | `main.py` line 277 | `config/constants.py` |

### Helper Functions
| Function | Before | After |
|----------|--------|-------|
| word_in_text | `main.py` lines 23-26 | `utils/helpers.py` |
| format_duration | `main.py` lines 169-181 | `utils/helpers.py` |
| is_event_in_window | `main.py` lines 132-168 | `utils/helpers.py` |

### Data Loaders
| Function | Before | After |
|----------|--------|-------|
| get_game_data | `main.py` lines 28-48 | `utils/data_loaders.py` |
| get_special_events | `main.py` lines 50-52 | `utils/data_loaders.py` |
| get_daily_templates | `main.py` lines 54-56 | `utils/data_loaders.py` |
| get_active_tasks | `main.py` lines 58-60 | `utils/data_loaders.py` |

### Task Manager
| Function | Before | After |
|----------|--------|-------|
| cleanup_expired_tasks | `main.py` lines 62-77 | `utils/task_manager.py` |
| get_active_tasks_in_window | `main.py` lines 79-92 | `utils/task_manager.py` |
| has_tasks_ending_in_window | `main.py` lines 94-106 | `utils/task_manager.py` |
| get_daily_activation_count | `main.py` lines 108-130 | `utils/task_manager.py` |

### Secretary Functions
| Function | Before | After |
|----------|--------|-------|
| get_secretary_event | `main.py` lines 206-211 | `utils/secretary.py` |
| save_secretary_event | `main.py` lines 213-217 | `utils/secretary.py` |

### Time Setup
| Component | Before | After |
|-----------|--------|-------|
| Time logic | `main.py` lines 219-288 | `utils/time_utils.py` |

### Pages
| Page | Before | After |
|------|--------|-------|
| Strategic Dashboard | `main.py` lines 294-928 | `pages/dashboard.py` |
| Weekly Calendar | `main.py` lines 932-1138 | `pages/weekly_calendar.py` |
| Arms Race Scheduler | `main.py` lines 1142-1303 | `pages/arms_scheduler.py` |
| VS Duel Manager | `main.py` lines 1307-1409 | `pages/vs_duel.py` |
| Special Events | `main.py` lines 1413-1504 | `pages/special_events.py` |
| Daily Tasks | `main.py` lines 1508-1769 | `pages/daily_tasks.py` |
| Calculator | `main.py` lines 1773-1878 | `pages/calculator.py` |
| Secretary Buffs | `main.py` lines 1882-2009 | `pages/secretary_buffs.py` |

## Rollback Instructions

If you need to revert to the monolithic version:

```bash
# Restore original main.py
cp src/app/main_original_backup.py src/app/main.py

# Remove new directories (optional)
rm -rf src/app/config src/app/utils src/app/pages src/app/components
```

## Testing Checklist

After migration, verify:

- [ ] App starts without errors
- [ ] All 8 pages are accessible via navigation
- [ ] Strategic Dashboard displays correctly with NOW indicator
- [ ] Arms Race Scheduler can save slot configurations
- [ ] VS Duel Manager shows schedule
- [ ] Special Events Manager can create/edit events
- [ ] Daily Tasks can be activated
- [ ] Secretary Buffs countdown displays
- [ ] Speed-Up Calculator computes correctly
- [ ] Time zones work correctly (server and local)
- [ ] Slot boundaries are correct (server [0,4,8,12,16,20])
- [ ] Data persists to CSV files
- [ ] Auto-refresh works on Dashboard (60s)

## Getting Help

**Issue:** Import errors
**Solution:** Ensure you're in the project root and Python path includes `src/`

**Issue:** Module not found
**Solution:** Check that all `__init__.py` files exist in directories

**Issue:** Circular import
**Solution:** Review `ARCHITECTURE.md` for dependency chain

## Benefits of New Architecture

1. **Easier Maintenance:** Each page is 100-700 lines instead of buried in 2010
2. **Better Testing:** Can unit test utilities without Streamlit
3. **Team Development:** Multiple devs can work on different pages
4. **Code Reuse:** Utilities shared across pages
5. **Clearer Structure:** Obvious where each piece of code lives

## Questions?

See `ARCHITECTURE.md` for detailed documentation on the new structure.

---

**Migration Date:** 2026-02-05
**Backup Location:** `src/app/main_original_backup.py`
