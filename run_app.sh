#!/bin/bash
# Convenience script to run the Last War Scheduler

# Activate virtual environment
source .venv/bin/activate

# Run the Streamlit app
streamlit run src/app/main.py

# Keep the script running to see output
wait
