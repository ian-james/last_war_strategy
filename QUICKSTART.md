# Quick Start Guide - Refactored Last War Scheduler

## Running the Application

### Option 1: Using the convenience script (Recommended)
```bash
./run_app.sh
```

### Option 2: Manual launch
```bash
source .venv/bin/activate
streamlit run src/app/main.py
```

### Option 3: From project root with Python
```bash
source .venv/bin/activate
cd src
streamlit run app/main.py
```

## Verifying the Installation

Run the automated verification:
```bash
source .venv/bin/activate
python verify_refactoring.py
```

Expected output: **✅ ALL TESTS PASSED!**

## Accessing the Application

Once running, the app will be available at:
- **Local:** http://localhost:8501
- **Network:** http://YOUR_IP:8501

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError: No module named 'app'`:
- Make sure you're running from the project root directory
- The path setup in `main.py` should handle this automatically

### Virtual Environment Not Found
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Port Already in Use
```bash
# Use a different port
streamlit run src/app/main.py --server.port=8502
```

## Navigation

The app has 8 pages accessible via the sidebar:

1. **Strategic Dashboard** - 24-hour optimization plan with NOW indicator
2. **Weekly 2× Calendar** - Weekly opportunities planner
3. **Arms Race Scheduler** - Configure weekly rotation
4. **VS Duel Manager** - Manage VS event schedule
5. **Special Events Manager** - Create/edit special events
6. **Secretary Buffs** - Track secretary position timers
7. **Daily Tasks Manager** - Activate and manage daily tasks
8. **Speed-Up Calculator** - Calculate speed-up requirements

## Key Features Preserved

✅ All original functionality intact
✅ Timezone support (server + local)
✅ Slot calculations (server hours: 0, 4, 8, 12, 16, 20)
✅ 24-hour optimization with NOW indicator
✅ Auto-refresh on dashboard (60s)
✅ Data persistence to CSV files
✅ Secretary buff countdown
✅ Daily task activation with limits

## What Changed?

**Architecture Only** - The functionality is 100% the same, but the code is now:
- **Modular**: 21 files instead of 1 monolithic file
- **Maintainable**: Each page is 100-700 lines instead of 2010
- **Testable**: Utilities can be unit tested
- **Organized**: Clear separation of config, utils, and pages

See `ARCHITECTURE.md` for full details.

## Rollback (If Needed)

To revert to the original monolithic version:
```bash
cp src/app/main_original_backup.py src/app/main.py
```

## Documentation

- **ARCHITECTURE.md** - Developer guide for the new structure
- **MIGRATION_GUIDE.md** - Code location reference (old → new)
- **REFACTORING_SUMMARY.md** - Implementation details
- **IMPLEMENTATION_COMPLETE.md** - Completion status

## Support

For issues or questions:
1. Check `ARCHITECTURE.md` for structure details
2. Check `MIGRATION_GUIDE.md` for code locations
3. Run `python verify_refactoring.py` to verify setup
4. Review the original code in `src/app/main_original_backup.py`

---

**Version:** 2.0.0 (Modularized)
**Last Updated:** 2026-02-05
