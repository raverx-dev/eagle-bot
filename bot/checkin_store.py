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
    does not exist, is empty, or encounters an error during parsing.

    This function first checks for the existence of the configured JSON file.
    If the file does not exist, it implies no linked player data has been
    saved yet, and an empty dictionary is returned to initialize USER_LINKS.
    If the file exists, it attempts to read and parse the JSON content.
    Error handling is included for file reading or JSON parsing issues,
    ensuring the bot's stability even with corrupted or malformed data files.
    The keys (Discord user IDs) are converted to integers upon loading, as
    JSON stores object keys as strings, but Discord IDs are numerical.
    """
    from bot.config import log

    log.info(f"CHK_LOAD: Attempting to load linked players from: {LINKED_PLAYERS_FILE}")
    if not os.path.exists(LINKED_PLAYERS_FILE):
        log.info("CHK_LOAD: Linked players file not found. Returning empty dictionary.")
        return {}

    try:
        log.info(f"CHK_LOAD: File found. Attempting to open and parse: {LINKED_PLAYERS_FILE}")
        with open(LINKED_PLAYERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            converted_data = {int(k): v for k, v in data.items()}
            log.info(f"CHK_LOAD: Successfully loaded {len(converted_data)} linked players.")
            return converted_data
    except (json.JSONDecodeError, IOError) as e:
        log.error(f"CHK_LOAD: Error loading linked players from {LINKED_PLAYERS_FILE}: {e}. Returning empty dictionary.")
        return {}

def save_linked_players(linked_players_data):
    """
    Saves the current linked player data to the persistent JSON file.
    This function ensures the data directory exists before writing the file.
    Any errors during file writing or JSON serialization are caught and logged.

    The keys (Discord user IDs) are converted to strings before saving, as
    JSON requires object keys to be strings.
    """
    from bot.config import log

    log.info(f"CHK_SAVE: Attempting to save linked players to: {LINKED_PLAYERS_FILE}")
    os.makedirs(DATA_DIR, exist_ok=True)

    try:
        log.info("CHK_SAVE: Directory ensured. Attempting to serialize and write data.")
        with open(LINKED_PLAYERS_FILE, 'w', encoding='utf-8') as f:
            serialized_data = {str(k): v for k, v in linked_players_data.items()}
            json.dump(serialized_data, f, indent=4)
            log.info(f"CHK_SAVE: Successfully saved {len(linked_players_data)} linked players.")
    except IOError as e:
        log.error(f"CHK_SAVE: Error saving linked players to {LINKED_PLAYERS_FILE}: {e}")
