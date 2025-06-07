# ──────────────────────────────────────────────────────────────────────────────
# FILE: bot/eagle_browser.py
# ──────────────────────────────────────────────────────────────────────────────

import os
import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Import configuration variables
from bot.config import EAGLE_EMAIL, EAGLE_PASSWORD, CHROME_DRIVER_PATH, \
    CHROME_USER_DATA_DIR, CHROME_PROFILE_DIR, log

# ──────────────────────────────────────────────────────────────────────────────
# A single “headed” Chrome instance for OAuth + an invisible headless one for scraping
# ──────────────────────────────────────────────────────────────────────────────
class EagleBrowser:
    def __init__(self):
        self.headless_driver = None

    def run_oauth_login(self, sdvx_id: str) -> bool:
        """
        Open a *visible* Chrome window to:
          1) Go to the SDVX profile URL → triggers OAuth redirect to kailua
          2) Fill in EAGLE_EMAIL & EAGLE_PASSWORD at the login form
          3) Click the “Authorize” (or “Allow”) button
          4) Wait until redirected back to the real Sound Voltex profile page
        This writes a valid eagle.ac cookie into CHROME_USER_DATA_DIR.
        """
        log.info("🔐 Starting OAuth login flow in a visible Chrome window…")

        options = Options()
        # Use the same profile folder so that cookies get saved to it:
        options.add_argument(f"--user-data-dir={CHROME_USER_DATA_DIR}")
        options.add_argument(f"--profile-directory={CHROME_PROFILE_DIR}")
        # Do not run headless here; we need to see the login page
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        service = Service(executable_path=CHROME_DRIVER_PATH)
        try:
            driver = webdriver.Chrome(service=service, options=options)
        except WebDriverException as e:
            log.error(f"❌ Could not launch Chrome for OAuth login: {e}")
            return False

        try:
            # Step A: Navigate to the SDVX profile URL. Eagle will redirect to OAuth login.
            target_url = f"https://eagle.ac/game/sdvx/profile/{sdvx_id}"
            driver.get(target_url)

            wait = WebDriverWait(driver, 15)

            # Step B: Fill in the Eagle login form (if present).
            try:
                email_fld = wait.until(EC.presence_of_element_located((By.NAME, "email")))
                pass_fld = driver.find_element(By.NAME, "password")
                email_fld.clear()
                email_fld.send_keys(EAGLE_EMAIL)
                pass_fld.clear()
                pass_fld.send_keys(EAGLE_PASSWORD)
                pass_fld.submit()
                log.info("✅ Submitted Eagle credentials.")
            except TimeoutException:
                # Possibly already logged in to kailua/eagle or no login form shown.
                log.info("ℹ️ No login form detected; assuming already logged into kailua/eagle.")

            # Step C: Wait for the “Authorize Application” button (it may say “Allow” or “Authorize”).
            try:
                authorize_btn = wait.until(EC.element_to_be_clickable(
                    (By.XPATH,
                     "//button[contains(text(),'Authorize') or contains(text(),'Allow') or contains(text(),'approve') or contains(text(),'Authorize Eagle Bot')]"
                    )
                ))
                authorize_btn.click()
                log.info("✅ Clicked ‘Authorize’ button.")
            except TimeoutException:
                log.info("ℹ️ No ‘Authorize’ button detected; maybe already authorized previously.")

            # Step D: Wait until the page title includes “Sound Voltex”
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
        Launch a headless ChromeDriver instance that reuses the profile directory,
        so we can scrape pages without any visible window.
        """
        log.info("☁️ Initializing headless ChromeDriver for scraping…")
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--user-data-dir={CHROME_USER_DATA_DIR}")
        options.add_argument(f"--profile-directory={CHROME_PROFILE_DIR}")

        service = Service(executable_path=CHROME_DRIVER_PATH)
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


# Create a single global browser object
BROWSER = EagleBrowser()
