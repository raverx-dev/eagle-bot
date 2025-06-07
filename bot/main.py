# ──────────────────────────────────────────────────────────────────────────────
# FILE: bot/main.py
# ──────────────────────────────────────────────────────────────────────────────

import threading
import datetime
import asyncio
import logging

import discord
from discord.ext import commands
from bs4 import BeautifulSoup

# Import settings from the new config module
from bot import config

# Selenium imports (for both headed OAuth automation & headless scraping)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# ──────────────────────────────────────────────────────────────────────────────
#  Basic logging setup
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("eagle_bot")

# ──────────────────────────────────────────────────────────────────────────────
#  In‐memory mapping: { discord_user_id (int) : sdvx_id (str) }
#  This will be moved to a storage manager in a later step.
# ──────────────────────────────────────────────────────────────────────────────
USER_LINKS = {
    # Example:
    # 123456789012345678: "95688187",
}

# ──────────────────────────────────────────────────────────────────────────────
#  A single “headed” Chrome instance for OAuth + an invisible headless one for scraping
# ──────────────────────────────────────────────────────────────────────────────
class EagleBrowser:
    def __init__(self):
        self.headless_driver = None

    def run_oauth_login(self, sdvx_id: str) -> bool:
        """
        Open a *visible* Chrome window to perform the OAuth login flow.
        """
        log.info("🔐 Starting OAuth login flow in a visible Chrome window…")

        options = Options()
        options.add_argument(f"--user-data-dir={config.CHROME_USER_DATA_DIR}")
        options.add_argument(f"--profile-directory={config.CHROME_PROFILE_DIR}")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        service = Service(executable_path=config.CHROME_DRIVER_PATH)
        try:
            driver = webdriver.Chrome(service=service, options=options)
        except WebDriverException as e:
            log.error(f"❌ Could not launch Chrome for OAuth login: {e}")
            return False

        try:
            target_url = f"https://eagle.ac/game/sdvx/profile/{sdvx_id}"
            driver.get(target_url)

            wait = WebDriverWait(driver, 15)

            try:
                email_fld = wait.until(EC.presence_of_element_located((By.NAME, "email")))
                pass_fld  = driver.find_element(By.NAME, "password")
                email_fld.clear()
                email_fld.send_keys(config.EAGLE_EMAIL)
                pass_fld.clear()
                pass_fld.send_keys(config.EAGLE_PASSWORD)
                pass_fld.submit()
                log.info("✅ Submitted Eagle credentials.")
            except TimeoutException:
                log.info("ℹ️  No login form detected; assuming already logged into kailua/eagle.")

            try:
                authorize_btn = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Authorize')]")
                ))
                authorize_btn.click()
                log.info("✅ Clicked ‘Authorize’ button.")
            except TimeoutException:
                log.info("ℹ️  No ‘Authorize’ button detected; maybe already authorized previously.")

            try:
                wait.until(EC.title_contains("Sound Voltex"))
                log.info("✅ OAuth login complete; session cookie for eagle.ac is now stored.")
            except TimeoutException:
                log.error("❌ Timeout waiting for redirection back to profile. OAuth may have failed.")
                driver.quit()
                return False

            driver.quit()
            return True

        except Exception as e:
            log.error(f"❌ Unexpected error during OAuth login flow: {e}")
            try:
                driver.quit()
            except:
                pass
            return False

    def init_headless_chrome(self) -> bool:
        """
        Launch a headless ChromeDriver instance that reuses the profile directory.
        """
        log.info("☁️  Initializing headless ChromeDriver for scraping…")
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--user-data-dir={config.CHROME_USER_DATA_DIR}")
        options.add_argument(f"--profile-directory={config.CHROME_PROFILE_DIR}")

        service = Service(executable_path=config.CHROME_DRIVER_PATH)
        try:
            self.headless_driver = webdriver.Chrome(service=service, options=options)
            log.info("✅ Headless ChromeDriver initialized successfully.")
            return True
        except WebDriverException as e:
            log.error(f"❌ Failed to initialize headless ChromeDriver: {e}")
            return False

    def quit_headless(self):
        if self.headless_driver:
            try:
                self.headless_driver.quit()
            except:
                pass
            self.headless_driver = None


BROWSER = EagleBrowser()

def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")

def scrape_profile_page(sdvx_id: str) -> dict:
    # This function will be moved in a later step
    pass

def scrape_leaderboard(arcade_id: str) -> list:
    # This function will be moved in a later step
    pass

def get_vf_from_arcade(sdvx_id: str) -> str:
    # This function will be moved in a later step
    pass

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    log.info(f"Bot is online as {bot.user} (ID {bot.user.id})")

# All bot commands will be moved to Cogs in later steps.
# For this cycle, we are only testing if the bot runs with the new config.

if __name__ == "__main__":
    bot.run(config.DISCORD_TOKEN)
