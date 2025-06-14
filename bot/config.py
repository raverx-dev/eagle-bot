import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# Logging Configuration
# ──────────────────────────────────────────────────────────────────────────────
log = logging.getLogger('eagle_bot')
log.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)

# ──────────────────────────────────────────────────────────────────────────────
# Discord Bot Configuration
# ──────────────────────────────────────────────────────────────────────────────
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# ──────────────────────────────────────────────────────────────────────────────
# Feature Toggles and Global Settings
# ──────────────────────────────────────────────────────────────────────────────
# Controls whether the automatic OAuth login process is enabled at startup.
# Set to 'True' or 'False' in the .env file. Defaults to True if not specified.
OAUTH_LOGIN_ENABLED = os.getenv('OAUTH_LOGIN_ENABLED', 'True').lower() == 'true'

EAGLE_EMAIL = os.getenv('EAGLE_EMAIL')
EAGLE_PASSWORD = os.getenv('EAGLE_PASSWORD')
CHROME_DRIVER_PATH = os.getenv('CHROME_DRIVER_PATH')
CHROME_USER_DATA_DIR = os.getenv('CHROME_USER_DATA_DIR')
CHROME_PROFILE_DIR = os.getenv('CHROME_PROFILE_DIR')
ARCADE_ID = os.getenv("ARCADE_ID", "94")

# Example: Base URL for Eagle's SDVX profile pages
# SDVX_PROFILE_BASE_URL = "https://eagle.ac/game/sdvx/profile/"

# Example: Base URL for Eagle's arcade leaderboard
# SDVX_LEADERBOARD_URL = "https://eagle.ac/game/sdvx/arcade_leaderboard"
