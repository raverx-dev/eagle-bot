"""
Configuration settings for the SV Bot project.

This module loads environment variables and defines constants used throughout
the application, centralizing all configurable parameters.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Discord Settings ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# --- Eagle.ac Login Credentials ---
EAGLE_EMAIL = os.getenv("EAGLE_EMAIL")
EAGLE_PASSWORD = os.getenv("EAGLE_PASSWORD")
ARCADE_ID = os.getenv("ARCADE_ID", "1")  # Default to '1' if not set

# --- Selenium and Chrome Driver Settings ---
# Ensure CHROME_DRIVER_PATH is correctly set to your chromedriver executable
CHROME_DRIVER_PATH = os.getenv("CHROME_DRIVER_PATH",
                               "/usr/bin/chromedriver")

# Define paths for Chrome user data and profile to persist cookies
# These directories will be created if they don't exist
# Reverting to the original path for existing cookie reuse
CHROME_USER_DATA_DIR = os.path.expanduser("~/.selenium_profiles/eaglebot_profile")
CHROME_PROFILE_DIR = "Default"
