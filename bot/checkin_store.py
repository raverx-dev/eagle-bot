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
