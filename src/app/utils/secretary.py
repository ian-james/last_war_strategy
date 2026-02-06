"""Secretary event management functions."""

import os
import json
from app.config.constants import SECRETARY_FILE


def get_secretary_event():
    """Return the active secretary event dict, or None.

    Returns:
        dict or None: Secretary event data if active, None otherwise
    """
    if not os.path.exists(SECRETARY_FILE):
        return None
    with open(SECRETARY_FILE) as f:
        return json.load(f)


def save_secretary_event(event):
    """Persist (or clear) the active secretary event.

    Args:
        event: Secretary event dict to save
    """
    with open(SECRETARY_FILE, "w") as f:
        json.dump(event, f)
