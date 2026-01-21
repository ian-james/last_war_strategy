# Project: Last Standing Tactician

## Project Overview
A Streamlit-based dashboard to track Alliance VS Duel events and Arms Race phases for "Last War: Survival". Optimized for HQ 25 and T8 troops.

## Technical Specs
- **Languages:** Python 3.11+
- **DateTime Lib:** Pendulum (Strictly used for all timezone/game reset logic)
- **UI Framework:** Streamlit
- **Data:** CSV (Tab-separated)
- **Timezone Base:** America/Halifax (Reset at 10:00 PM local)

## Game Data Context
- **HQ Level:** 25
- **Troop Level:** 8 (T8)
- **VS Rotation:** 
  - Mon: Radar
  - Tue: Base Expansion
  - Wed: Age of Science
  - Thu: Train Heroes
  - Fri: Total Mobilization
  - Sat: Enemy Buster
  - Sun: Rest Day (Free)

## File Structure
- `src/app.py`: Main dashboard logic.
- `data/last_standing_schedule.csv`: Points and tasks database.
- `pyproject.toml`: Dependencies (streamlit, pandas, pendulum).
