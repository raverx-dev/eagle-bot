import datetime
import json
import os

# ──────────────────────────────────────────────────────────────────────────────
# Persistent Data Storage Configuration
# This section defines the directory and file path for storing linked player
# data persistently across bot sessions. Linked player data includes Discord
# user IDs mapped to their corresponding Sound Voltex IDs.
# ──────────────────────────────────────────────────────────────────────────────
DATA_DIR = 'data'
LINKED_PLAYERS_FILE = os.path.join(DATA_DIR, 'linked_players.json')

# ──────────────────────────────────────────────────────────────────────────────
# In‐memory mapping: { discord_user_id (int) : sdvx_id (str) }
# Admins must run !linkid once per Discord user to populate this.
# ──────────────────────────────────────────────────────────────────────────────
USER_LINKS = {
    # Example:
    # 123456789012345678: "95688187",
}

# ──────────────────────────────────────────────────────────────────────────────
# Check-in store: { discord_user_id: { "time": datetime, "plays": int, "vf": float } }
# ──────────────────────────────────────────────────────────────────────────────
CHECKIN_STORE = {}

# ──────────────────────────────────────────────────────────────────────────────
# Linked Players Persistence
# Functions for loading and saving the USER_LINKS dictionary to a JSON file
# for persistent storage.
# ──────────────────────────────────────────────────────────────────────────────
def load_linked_players():
    """
    Loads linked player data from the persistent JSON file.
    Returns a dictionary of linked players or an empty dictionary if the file
    does not exist or is empty.

    This function first checks for the existence of the configured JSON file.
    If the file does not exist, it implies no linked player data has been
    saved yet, and an empty dictionary is returned to initialize USER_LINKS.
    The next step will involve reading and parsing the file if it exists.
    """
    if not os.path.exists(LINKED_PLAYERS_FILE):
        return {}
