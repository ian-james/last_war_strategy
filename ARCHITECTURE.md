# Last War Scheduler - Architecture Guide

## Overview

The Last War Scheduler is now a modular Streamlit application with clean separation of concerns.

## Directory Structure

```
src/app/
├── main.py                    # Application entry point
├── config/                    # Configuration and constants
│   ├── constants.py          # File paths, mappings, game data
│   └── __init__.py
├── utils/                     # Utility functions
│   ├── helpers.py            # Pure helper functions
│   ├── data_loaders.py       # CSV/JSON loading functions
│   ├── task_manager.py       # Active task lifecycle management
│   ├── secretary.py          # Secretary event persistence
│   ├── time_utils.py         # Timezone and time calculations
│   └── __init__.py
├── pages/                     # Page rendering modules
│   ├── dashboard.py          # Strategic Dashboard
│   ├── weekly_calendar.py    # Weekly 2× Calendar
│   ├── arms_scheduler.py     # Arms Race Scheduler
│   ├── vs_duel.py            # VS Duel Manager
│   ├── special_events.py     # Special Events Manager
│   ├── daily_tasks.py        # Daily Tasks Manager
│   ├── calculator.py         # Speed-Up Calculator
│   ├── secretary_buffs.py    # Secretary Buffs
│   └── __init__.py
└── components/                # Reusable UI components (future)
    └── __init__.py
```

## Module Responsibilities

### `main.py`
**Purpose:** Application entry point and routing

**Responsibilities:**
- Set page configuration
- Setup sidebar navigation
- Initialize time context via `setup_timezone_and_time()`
- Load game data and special events
- Cleanup expired tasks
- Route to appropriate page based on navigation

**Size:** 94 lines

### `config/constants.py`
**Purpose:** Centralized configuration and constants

**Exports:**
- File paths (8 CSV/JSON file paths)
- `OVERLAP_MAP` - Event overlap detection for 2× opportunities
- `SECRETARIES` - Secretary buff definitions with icons and bonuses
- `SLOT_START_HOURS` - Server time boundaries [0, 4, 8, 12, 16, 20]

**Size:** 49 lines

### `utils/helpers.py`
**Purpose:** Pure helper functions with no side effects

**Functions:**
- `word_in_text(keyword, text)` - Case-insensitive whole-word matching
- `format_duration(total_minutes)` - Format minutes to "2d 4h" or "1h 30m"
- `is_event_in_window(event_row, window_start)` - Check special event overlap

**Size:** 61 lines

### `utils/data_loaders.py`
**Purpose:** CSV and JSON data loading functions

**Functions:**
- `get_game_data()` - Load and merge Arms Race + VS Duel schedules
- `get_special_events()` - Load special events CSV
- `get_daily_templates()` - Load daily task templates
- `get_active_tasks()` - Load active tasks from CSV

**Size:** 63 lines

### `utils/task_manager.py`
**Purpose:** Active task lifecycle management

**Functions:**
- `cleanup_expired_tasks()` - Remove past tasks from active list
- `get_active_tasks_in_window(start_utc, end_utc)` - Tasks overlapping window
- `has_tasks_ending_in_window(start_utc, end_utc)` - Check for task completions
- `get_daily_activation_count(task_name, now_srv)` - Count today's activations

**Size:** 116 lines

### `utils/secretary.py`
**Purpose:** Secretary event persistence

**Functions:**
- `get_secretary_event()` - Load active secretary buff from JSON
- `save_secretary_event(event)` - Persist secretary buff to JSON

**Size:** 27 lines

### `utils/time_utils.py`
**Purpose:** Timezone configuration and time calculations

**Functions:**
- `setup_timezone_and_time()` - Render sidebar time config, calculate all times

**Returns:** Dictionary with keys:
```python
{
    'server_tz': pendulum.timezone,
    'server_tz_label': str,
    'user_tz': pendulum.timezone or str,
    'user_tz_label': str,
    'fmt': str,  # "HH:mm" or "h:mm A"
    'now_utc': pendulum.DateTime,
    'now_server': pendulum.DateTime,
    'now_local': pendulum.DateTime,
    'current_slot': int,  # 1-6
    'active_start': pendulum.DateTime,
    'game_day_start': pendulum.DateTime,
    'vs_day': str,  # "Monday", "Tuesday", etc.
    'ar_day': str,
}
```

**Size:** 106 lines

### `pages/*.py`
**Purpose:** Individual page rendering modules

**Pattern:**
```python
def render(time_ctx: dict, *args, **kwargs):
    """Render the [Page Name] page.

    Args:
        time_ctx: Dictionary from setup_timezone_and_time()
        *args: Page-specific dependencies (df, specials_df, etc.)
    """
    # Extract needed values from time_ctx
    now_server = time_ctx['now_server']
    user_tz = time_ctx['user_tz']
    fmt = time_ctx['fmt']

    # Page content
    st.title("...")
    # ...
```

**Sizes:**
- `dashboard.py`: 686 lines (most complex)
- `daily_tasks.py`: 299 lines
- `weekly_calendar.py`: 226 lines
- `arms_scheduler.py`: 182 lines
- `secretary_buffs.py`: 150 lines
- `special_events.py`: 123 lines
- `calculator.py`: 116 lines
- `vs_duel.py`: 115 lines

## Dependency Chain

```
main.py
  ↓
  ├── config.constants
  ├── utils.time_utils → config.constants
  ├── utils.data_loaders → config.constants
  ├── utils.task_manager → config.constants, utils.data_loaders
  └── pages.*
      ├── dashboard → config.constants, utils.*
      ├── weekly_calendar → config.constants, utils.helpers, utils.data_loaders
      ├── arms_scheduler → config.constants, utils.data_loaders
      ├── vs_duel → config.constants
      ├── special_events → config.constants, utils.data_loaders
      ├── daily_tasks → config.constants, utils.data_loaders, utils.task_manager
      ├── calculator → utils.helpers
      └── secretary_buffs → config.constants, utils.secretary
```

**Key Principle:** No circular dependencies. Pages never import from other pages.

## Time Context Pattern

All pages receive a `time_ctx` dictionary with standardized time values. This ensures:
1. Consistent timezone handling across pages
2. Single source of truth for current time
3. Easy testing (can mock the dictionary)

## Data Flow

```
User navigates → main.py
                  ↓
            Setup time context
                  ↓
            Load game data
                  ↓
            Cleanup expired tasks
                  ↓
            Route to page
                  ↓
            Page.render(time_ctx, ...)
                  ↓
            Display UI
```

## Critical Game Rules

### Slot Calculation
```python
current_slot = (now_server.hour // 4) + 1  # 1-6
```

**Server boundaries:** [0, 4, 8, 12, 16, 20] hours

| Slot | Server (UTC-2) | Halifax (UTC-4) |
|------|---------------|-----------------|
| 1    | 00:00–04:00   | 22:00–02:00     |
| 2    | 04:00–08:00   | 02:00–06:00     |
| 3    | 08:00–12:00   | 06:00–10:00     |
| 4    | 12:00–16:00   | 10:00–14:00     |
| 5    | 16:00–20:00   | 14:00–18:00     |
| 6    | 20:00–00:00   | 18:00–22:00     |

### Timezone Architecture
- **Backend storage:** UTC+0 (all CSV timestamps)
- **Server timezone:** UTC-2 (game server, user-selectable dropdown)
- **Local timezone:** User-selectable (e.g., America/Halifax = UTC-4)
- **Server timezone is ONLY changed by user in UI dropdown — never programmatically**

### Game Day Reset
- Game day resets at **00:00 server time** (midnight server = 22:00 Halifax)
- Thursday schedule runs midnight-to-midnight server time

## Adding a New Page

1. **Create page module** in `src/app/pages/your_page.py`
2. **Define render function:**
   ```python
   def render(time_ctx: dict):
       st.title("Your Page")
       # Implementation
   ```
3. **Import in** `src/app/pages/__init__.py`
4. **Add navigation option** in `main.py`:
   ```python
   elif page == "Your Page":
       your_page.render(time_ctx)
   ```

## Adding a New Utility

1. **Create utility module** in `src/app/utils/your_util.py`
2. **Define functions**
3. **Export in** `src/app/utils/__init__.py`
4. **Import where needed:**
   ```python
   from app.utils.your_util import your_function
   ```

## Testing

### Unit Tests
Test utilities in isolation:
```python
from app.utils.helpers import format_duration

def test_format_duration():
    assert format_duration(90) == "1h 30m"
    assert format_duration(1440) == "1d"
```

### Integration Tests
Test page rendering with mock time context:
```python
import streamlit as st
from app.pages import calculator

def test_calculator_page():
    time_ctx = {
        'now_server': pendulum.now('UTC-2'),
        'user_tz': 'America/Halifax',
        'fmt': 'HH:mm',
        # ...
    }
    calculator.render(time_ctx)
    # Assert expected outputs
```

## Best Practices

1. **Never mutate time_ctx** - Treat as read-only
2. **Extract all needed values** at start of render function
3. **Use constants from config** - Don't hardcode file paths or mappings
4. **Session state keys** - Prefix with page name to avoid conflicts
5. **Error handling** - Wrap file I/O in try-except
6. **Type hints** - Add for function signatures (optional but recommended)

## Performance Considerations

1. **Data loading** - CSV files loaded once per page load (not per rerun)
2. **Cleanup** - Expired tasks cleaned up on every main.py load
3. **Auto-refresh** - Dashboard refreshes every 60s via JavaScript
4. **Session state** - Persists across st.rerun() but not browser refresh

## Future Enhancements

1. **components/ui_components.py** - Extract reusable UI patterns
2. **Type annotations** - Add full type hints to all functions
3. **Unit tests** - Add pytest test suite
4. **API layer** - Abstract data access for easier mocking
5. **Config file** - Move hardcoded values to YAML/JSON config

---

**Last Updated:** 2026-02-05
**Version:** 2.0.0 (Modularized)
