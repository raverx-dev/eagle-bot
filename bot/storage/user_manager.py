"""
Manages the loading and saving of user link data to 'watched_players.json'.

This module provides functions to persist the mapping of Discord user IDs
to SDVX IDs, ensuring user configurations are retained across bot sessions.
"""
import json
import logging
import os

log = logging.getLogger(__name__)

USER_LINKS_FILE = "watched_players.json"


def load_users() -> dict:
    """
    Loads Discord-SDVX ID links from the JSON file.

    If the file does not exist or is corrupt, an empty dictionary is returned.

    Returns:
        A dictionary mapping Discord user IDs (str) to SDVX IDs (str).
    """
    if not os.path.exists(USER_LINKS_FILE):
        log.info(f"{USER_LINKS_FILE} not found. Creating empty file.")
        try:
            with open(USER_LINKS_FILE, 'w') as f:
                json.dump({}, f)
            return {}
        except IOError as e:
            log.error(f"Error creating {USER_LINKS_FILE}: {e}")
            return {}

    try:
        with open(USER_LINKS_FILE, 'r') as f:
            user_links = json.load(f)
            # Ensure loaded data is a dictionary
            if not isinstance(user_links, dict):
                log.error(f"Content of {USER_LINKS_FILE} is not a valid JSON "
                          "object (dictionary). Resetting to empty.")
                return {}
            return user_links
    except json.JSONDecodeError as e:
        log.error(f"Error decoding JSON from {USER_LINKS_FILE}: {e}. "
                  "File might be corrupt. Returning empty dictionary.")
        return {}
    except IOError as e:
        log.error(f"Error reading {USER_LINKS_FILE}: {e}. "
                  "Returning empty dictionary.")
        return {}


def save_users(user_links: dict):
    """
    Saves Discord-SDVX ID links to the JSON file.

    Args:
        user_links: The dictionary of user links to save.
    """
    try:
        with open(USER_LINKS_FILE, 'w') as f:
            json.dump(user_links, f, indent=4)
        log.info(f"User links saved to {USER_LINKS_FILE}.")
    except IOError as e:
        log.error(f"Error saving {USER_LINKS_FILE}: {e}")
