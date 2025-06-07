# ──────────────────────────────────────────────────────────────────────────────
# FILE: bot/config.py
# ──────────────────────────────────────────────────────────────────────────────

import os
import logging
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────────────────
# Load environment variables
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
if not DISCORD_BOT_TOKEN:
    raise RuntimeError("You must set DISCORD_BOT_TOKEN in .env")

EAGLE_EMAIL = os.getenv("EAGLE_EMAIL", "").strip()
EAGLE_PASSWORD = os.getenv("EAGLE_PASSWORD", "").strip()
if not (EAGLE_EMAIL and EAGLE_PASSWORD):
    raise RuntimeError("You must set EAGLE_EMAIL and EAGLE_PASSWORD in .env")

# ──────────────────────────────────────────────────────────────────────────────
# Paths to ChromeDriver & Chrome user-data
# ──────────────────────────────────────────────────────────────────────────────
CHROME_DRIVER_PATH = "/usr/bin/chromedriver"  # Adjust if your chromedriver lives elsewhere

# We will store (and later reuse) the “logged-in” Eagle session cookie here:
CHROME_USER_DATA_DIR = os.path.expanduser("~/.selenium_profiles/eaglebot_profile")
CHROME_PROFILE_DIR = "Default"

# ──────────────────────────────────────────────────────────────────────────────
# Basic logging setup
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("eagle_bot")

# ──────────────────────────────────────────────────────────────────────────────
# Arcade ID
# ──────────────────────────────────────────────────────────────────────────────
ARCADE_ID = "94"  # ← change to your own arcade number if it’s different
