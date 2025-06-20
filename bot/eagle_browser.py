# bot/eagle_browser.py
import os
import asyncio
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, InvalidSessionIdException

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
        driver = None
        try:
            driver = webdriver.Chrome(service=service, options=options)
            wait = WebDriverWait(driver, 15)
            target_url = f"https://eagle.ac/game/sdvx/profile/{sdvx_id}"
            driver.get(target_url)

            try:
                log.info("Looking for main login button...")
                main_login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='https://eagle.ac/auth/kailua']")))
                log.info("✅ Main login button found, clicking it.")
                main_login_button.click()
            except TimeoutException:
                log.info("ℹ️ Did not find main login button, assuming direct redirect to form.")
            try:
                email_fld = wait.until(EC.presence_of_element_located((By.NAME, "email")))
                pass_fld = driver.find_element(By.NAME, "password")
                email_fld.clear(); email_fld.send_keys(EAGLE_EMAIL)
                pass_fld.clear(); pass_fld.send_keys(EAGLE_PASSWORD)
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

            wait.until(EC.title_contains("Sound Voltex"))
            log.info("✅ OAuth login complete.")
            return True
        except Exception as e:
            log.error(f"❌ Unexpected error during OAuth login flow: {e}", exc_info=True)
            return False
        finally:
            if driver:
                driver.quit()

    def init_headless_chrome(self) -> bool:
        log.info("☁️ Initializing headless ChromeDriver for scraping…")
        options = Options()
        options.add_argument("--headless=new"); options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox"); options.add_argument("--disable-dev-shm-usage")
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
            try:
                self.headless_driver.quit()
                log.info("⚪️ Headless browser closed.")
            except Exception as e:
                log.warning(f"Could not quit headless browser gracefully: {e}")
            finally:
                self.headless_driver = None

    def is_alive(self) -> bool:
        if not self.headless_driver: return False
        try:
            _ = self.headless_driver.title
            return True
        except WebDriverException:
            return False

    async def ensure_browser_is_ready(self):
        if not self.is_alive():
            log.warning("Browser session is not alive. Attempting to restart...")
            self.quit_headless()
            if not await asyncio.to_thread(self.init_headless_chrome):
                raise RuntimeError("Headless browser is unavailable and could not be restarted.")

    def _scrape_leaderboard_sync(self) -> list:
        log.info("BACKGROUND SCRAPE: Getting leaderboard page...")
        url = f"https://eagle.ac/arcade/{ARCADE_ID}"
        self.headless_driver.get(url)
        try:
            WebDriverWait(self.headless_driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'panel-primary') and .//h3[contains(text(), 'Arcade Top 10')]]")))
            html = self.headless_driver.page_source
        except TimeoutException:
            log.error("SCRAPER: Timed out waiting for leaderboard panel to load.")
            return []
        soup = BeautifulSoup(html, "html.parser")
        panel_h3 = soup.find("h3", class_="panel-title", string=lambda t: t and "Arcade Top 10" in t)
        if not panel_h3:
            return []
        lead_table = panel_h3.find_parent("div", class_="panel-primary").find("table", class_="table")
        if not lead_table:
            return []
        output = []
        for row in lead_table.select("tbody > tr"):
            cols = row.find_all("td")
            if len(cols) < 4: continue
            try:
                rank = int(cols[0].get_text(strip=True))
                vf_val = float(cols[3].get_text(strip=True))
                output.append({"rank": rank, "sdvx_id": cols[1].get_text(strip=True), "player_name": cols[2].get_text(strip=True), "volforce": vf_val})
            except (ValueError, TypeError):
                log.warning(f"SCRAPER: Could not parse row: {cols}")
                continue
        log.info(f"BACKGROUND SCRAPE: Found {len(output)} players on leaderboard.")
        return output

    async def scrape_leaderboard(self) -> list:
        await self.ensure_browser_is_ready()
        try:
            return await asyncio.to_thread(self._scrape_leaderboard_sync)
        except InvalidSessionIdException:
            log.warning("Caught InvalidSessionIdException during leaderboard scrape. Retrying once...")
            await self.ensure_browser_is_ready()
            return await asyncio.to_thread(self._scrape_leaderboard_sync)

    def _scrape_player_profile_sync(self, sdvx_id: str) -> dict:
        url = f"https://eagle.ac/game/sdvx/profile/{sdvx_id}"
        log.debug(f"SCRAPER: Getting player profile page for {sdvx_id}...")
        self.headless_driver.get(url)
        try:
            WebDriverWait(self.headless_driver, 10).until(EC.presence_of_element_located((By.ID, "playstable")))
            html = self.headless_driver.page_source
        except TimeoutException:
            log.warning(f"SCRAPER: Timed out waiting for Score Log table for {sdvx_id}.")
            return {}

        soup = BeautifulSoup(html, "html.parser")
        player_name, volforce, skill_level, total_plays = None, None, None, None

        name_div = soup.select_one("h2.page-header div.col-xs-7")
        if name_div:
            player_name = name_div.find(text=True, recursive=False).strip()

        try:
            skill_level_b_tag = soup.find("b", string="Skill Level:")
            if skill_level_b_tag and skill_level_b_tag.find_next_sibling("i"):
                skill_level = skill_level_b_tag.find_next_sibling("i").get_text(strip=True)
        except Exception as e:
            log.warning(f"SCRAPER: Could not parse Skill Level for {sdvx_id}: {e}")
        try:
            total_plays_b_tag = soup.find("b", string="Plays:")
            if total_plays_b_tag:
                value_string = list(total_plays_b_tag.parent.stripped_strings)[-1]
                total_plays = int(value_string.replace(',', ''))
        except Exception as e:
            log.warning(f"SCRAPER: Could not parse Total Plays for {sdvx_id}: {e}")

        recent_plays = []
        play_table = soup.find("table", id="playstable")
        if play_table:
            for row in play_table.select("tbody > tr"):
                if "accordion-toggle" not in row.get("class", []): continue
                cols = row.find_all("td")
                if len(cols) < 8: continue
                try:
                    recent_plays.append({
                        "song_title": cols[1].find("b").get_text(strip=True) if cols[1].find("b") else None,
                        "chart": cols[2].get_text(strip=True),
                        "clear_type": cols[3].find("strong").get_text(strip=True),
                        "grade": cols[4].find("strong").get_text(strip=True),
                        "score": cols[5].get_text(strip=True),
                        "vf_per_play": float(cols[6].get_text(strip=True)) if cols[6].get_text(strip=True) else None,
                        "timestamp": cols[7].find("small").get_text(strip=True),
                        "is_new_record": bool(cols[0].find("i", class_="fa fa-star"))
                    })
                except Exception as e:
                    # RESTORED: Logging for row parse errors
                    log.warning(f"SCRAPER: Could not parse a play row for {sdvx_id}. Error: {e}")
                    continue
        
        log.debug(f"SCRAPER: Profile scraped for {sdvx_id}. Name: {player_name}, Recent Plays: {len(recent_plays)}")
        return { 
            "player_name": player_name,
            "skill_level": skill_level,
            "total_plays": total_plays,
            "recent_plays": recent_plays 
        }

    async def scrape_player_profile(self, sdvx_id: str) -> dict:
        await self.ensure_browser_is_ready()
        try:
            return await asyncio.to_thread(self._scrape_player_profile_sync, sdvx_id)
        except InvalidSessionIdException:
            log.warning("Caught InvalidSessionIdException during profile scrape. Retrying once...")
            await self.ensure_browser_is_ready()
            return await asyncio.to_thread(self._scrape_player_profile_sync, sdvx_id)