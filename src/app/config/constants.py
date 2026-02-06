"""Constants for file paths, event mappings, and game data."""

# --- FILE PATHS ---
DATA_FILE = "data/last_standing_schedule.csv"  # Legacy file (for backward compatibility)
ARMS_RACE_FILE = "data/arms_race_schedule.csv"
VS_DUEL_FILE = "data/vs_duel_schedule.csv"
SPECIAL_FILE = "data/special_events.csv"
DAILY_TEMPLATES_FILE = "data/daily_task_templates.csv"
ACTIVE_TASKS_FILE = "data/active_daily_tasks.csv"
RESTORE_TEMPLATES_FILE = "data/restore_daily_task_templates.csv"
SECRETARY_FILE = "data/secretary_event.json"

# --- SLOT CONFIGURATION ---
# Server time boundaries for 6 slots (each 4 hours)
SLOT_START_HOURS = [0, 4, 8, 12, 16, 20]

# --- OVERLAP MAPPING FOR 2× DETECTION ---
OVERLAP_MAP = {
    "Base": ["Building Power", "Construction Speedup", "Building", "Construction"],
    "Tech": ["Tech Power", "Research Speedup", "Research"],
    "Hero": ["Hero Recruitment", "Hero EXP", "Hero Shard", "Hero", "Recruitment"],
    "Unit": ["Train T8 Unit", "Training Speedup", "Training", "Train", "Unit"],
    "Drone": ["Drone Data Point", "Drone Component", "Drone Part", "Stamina", "Drone"],
    "All-Rounder": ["Hero", "Building", "Research", "Train", "Construction", "Drone"]
}

# --- SECRETARY BUFFS ---
SECRETARIES = {
    "Secretary of Strategy": {
        "icon": "🏥",
        "bonuses": [("Hospital Capacity", "+20%"), ("Unit Healing", "+20%")],
    },
    "Secretary of Defense": {
        "icon": "⚔️",
        "bonuses": [("Unit Training Cap", "+20%"), ("Training Speed", "+20%")],
    },
    "Secretary of Development": {
        "icon": "🏗️",
        "bonuses": [("Construction Speed", "+50%"), ("Research Speed", "+25%")],
    },
    "Secretary of Science": {
        "icon": "🔬",
        "bonuses": [("Research Speed", "+50%"), ("Construction Speed", "+25%")],
    },
    "Secretary of Interior": {
        "icon": "🏘️",
        "bonuses": [("Food", "+100%"), ("Iron", "+100%"), ("Coin", "+100%")],
    },
}
