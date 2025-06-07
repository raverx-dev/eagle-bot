import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot and API credentials
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
EAGLE_EMAIL    = os.getenv("EAGLE_EMAIL")
EAGLE_PASSWORD = os.getenv("EAGLE_PASSWORD")

# Path and ID configurations
CHROME_DRIVER_PATH = "/usr/bin/chromedriver"
CHROME_USER_DATA_DIR = os.path.expanduser("~/.selenium_profiles/eaglebot_profile")
CHROME_PROFILE_DIR   = "Default"
ARCADE_ID = "94"

# Validate that secrets are set
if not all([DISCORD_TOKEN, EAGLE_EMAIL, EAGLE_PASSWORD]):
    raise RuntimeError("One or more required environment variables are not set in the .env file.")
