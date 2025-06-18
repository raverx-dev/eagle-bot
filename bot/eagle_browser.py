# bot/eagle_browser.py
import os
import logging
import asyncio
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from bot.config import (
    EAGLE_EMAIL, EAGLE_PASSWORD, CHROME_DRIVER_PATH,
    CHROME_USER_DATA_DIR, CHROME_PROFILE_DIR, log, ARCADE_ID
)

class EagleBrowser:
    def __init__(self):
        self.headless_driver = None

    def run_oauth_login(self, sdvx_id: str) -> bool:
        log.info("🔐 Starting OAuth login flow in a visible Chrome window…")
        options = Options()
        options.add_argument(f"--user-data-dir={CHROME_USER_DATA_DIR}")
        options.add_argument(f"--profile-directory={CHROME_PROFILE_DIR}")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        service = Service(executable_path=CHROME_DRIVER_PATH)
        try:
            driver = webdriver.Chrome(service=service, options=options)
            wait = WebDriverWait(driver, 15)
        except WebDriverException as e:
            log.error(f"❌ Could not launch Chrome for OAuth login: {e}")
            return False

        try:
            target_url = f"https://eagle.ac/game/sdvx/profile/{sdvx_id}"
            driver.get(target_url)

            try:
                log.info("Looking for main login button...")
                main_login_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='https://eagle.ac/auth/kailua']"))
                )
                log.info("✅ Main login button found, clicking it.")
                main_login_button.click()
            except TimeoutException:
                log.info("ℹ️ Did not find main login button, assuming direct redirect to form.")

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
                log.info("ℹ️ No login form detected; assuming already logged in.")

            try:
                authorize_btn = wait.until(EC.element_to_be_clickable((By.XPATH,"//button[contains(text(),'Authorize') or contains(text(),'Allow')]")))
                authorize_btn.click()
                log.info("✅ Clicked ‘Authorize’ button.")
            except TimeoutException:
                log.info("ℹ️ No ‘Authorize’ button detected; maybe already authorized.")

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
            log.error(f"❌ Unexpected error during OAuth login flow: {e}", exc_info=True)
            try:
                driver.quit()
            except:
                pass
            return False

    def init_headless_chrome(self) -> bool:
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
        except Exception as e:
            log.error(f"❌ Failed to initialize headless ChromeDriver: {e}", exc_info=True)
            return False

    def quit_headless(self):
        if self.headless_driver:
            self.headless_driver.quit()

    def _scrape_leaderboard_sync(self) -> list:
        log.info("BACKGROUND SCRAPE: Getting leaderboard page...") # Keep this as INFO
        url = f"https://eagle.ac/arcade/{ARCADE_ID}"
        self.headless_driver.get(url)
        try:
            WebDriverWait(self.headless_driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'panel-primary') and .//h3[contains(text(), 'Arcade Top 10')]]"))
            )
            html = self.headless_driver.page_source
        except TimeoutException:
            log.error("SCRAPER: Timed out waiting for leaderboard panel to load.")
            return []
        soup = BeautifulSoup(html, "html.parser")
        panel_h3 = soup.find("h3", class_="panel-title", string=lambda t: t and "Arcade Top 10" in t)
        if not panel_h3:
            log.warning("SCRAPER: Could not find H3 in parsed soup.")
            return []
        lead_table = panel_h3.find_parent("div", class_="panel-primary").find("table", class_="table")
        if not lead_table:
            log.warning("SCRAPER: Could not find table in parsed soup.")
            return []
        output = []
        for row in lead_table.select("tbody > tr"):
            cols = row.find_all("td")
            if len(cols) < 4: continue
            try:
                rank = int(cols[0].get_text(strip=True))
                vf_val = float(cols[3].get_text(strip=True))
                sdvx_id = cols[1].get_text(strip=True)
                name = cols[2].get_text(strip=True)
                output.append({"rank": rank, "sdvx_id": sdvx_id, "player_name": name, "volforce": vf_val})
            except (ValueError, TypeError):
                log.warning(f"SCRAPER: Could not parse row: {cols}")
                continue
        log.info(f"BACKGROUND SCRAPE: Found {len(output)} players on leaderboard.") # Keep this as INFO
        return output

    async def scrape_leaderboard(self) -> list:
        if not self.headless_driver:
            log.error("❌ Headless browser not initialized. Cannot scrape.")
            return []
        return await asyncio.to_thread(self._scrape_leaderboard_sync)

    async def scrape_player_profile(self, sdvx_id: str) -> dict:
        if not self.headless_driver:
            log.error("❌ Headless browser not initialized. Cannot scrape player profile.")
            return {}

        def _sync_scrape_profile():
            url = f"https://eagle.ac/game/sdvx/profile/{sdvx_id}"
            log.debug(f"SCRAPER: Getting player profile page for {sdvx_id}...") # This is already DEBUG
            self.headless_driver.get(url)
            try:
                WebDriverWait(self.headless_driver, 10).until(
                    EC.presence_of_element_located((By.ID, "playstable"))
                )
                html = self.headless_driver.page_source
            except TimeoutException:
                log.warning(f"SCRAPER: Timed out waiting for Score Log table for {sdvx_id}.")
                return { "player_name": None, "recent_plays": [] }

            soup = BeautifulSoup(html, "html.parser")
            player_name = None
            name_div = soup.select_one("h2.page-header div.col-xs-7")
            if name_div:
                try:
                    player_name = name_div.find(text=True, recursive=False).strip()
                except Exception:
                    player_name = None

            recent_plays = []
            play_table = soup.find("table", id="playstable")
            if play_table:
                for row in play_table.select("tbody > tr"):
                    if "accordion-toggle" not in row.get("class", []):
                        continue
                    cols = row.find_all("td")
                    if len(cols) < 8: continue
                    try:
                        song_title = cols[1].find("b").get_text(strip=True) if cols[1].find("b") else None
                        chart = cols[2].get_text(strip=True) if cols[2] else None
                        clear_type = cols[3].find("strong").get_text(strip=True) if cols[3].find("strong") else None
                        grade = cols[4].find("strong").get_text(strip=True) if cols[4].find("strong") else None
                        score_val = cols[5].get_text(strip=True) if cols[5] else None
                        vf_per_play = float(cols[6].get_text(strip=True)) if cols[6] and cols[6].get_text(strip=True) else None
                        timestamp = cols[7].find("small").get_text(strip=True) if cols[7].find("small") else None
                        is_new_record = bool(cols[0].find("i", class_="fa fa-star"))
                        recent_plays.append({
                            "song_title": song_title, "chart": chart, "clear_type": clear_type,
                            "grade": grade, "score": score_val, "vf_per_play": vf_per_play,
                            "timestamp": timestamp, "is_new_record": is_new_record
                        })
                    except Exception as e:
                        log.warning(f"SCRAPER: Could not parse a play row for {sdvx_id}. Error: {e}")

            # --- LOGGING CHANGE ---
            # This is the spammy message. Changed from INFO to DEBUG.
            log.debug(f"SCRAPER: Profile scraped for {sdvx_id}. Name: {player_name}, Recent Plays: {len(recent_plays)}")
            return { "player_name": player_name, "recent_plays": recent_plays }

        return await asyncio.to_thread(_sync_scrape_profile)