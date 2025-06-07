"""
Manages the Selenium WebDriver for all web scraping tasks.

This module contains the EagleBrowser class, which is responsible for
both the initial, visible OAuth login flow and the subsequent headless
scraping of the eagle.ac website.
"""
import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from .. import config

log = logging.getLogger(__name__)


class EagleBrowser:
    """
    A singleton-like class to manage a persistent Selenium
    browser session.
    """
    def __init__(self):
        """Initializes the browser wrapper with no active driver."""
        self.headless_driver = None

    def run_oauth_login(self, sdvx_id: str) -> bool:
        """
        Performs the initial OAuth login using a visible browser window.

        This method navigates to the eagle.ac login page, submits the
        credentials stored in the bot's configuration, and waits for
        a successful redirection. The resulting session cookie is stored
        in the user data directory for the headless browser to reuse.

        Args:
            sdvx_id: A valid SDVX ID needed to trigger the login redirect.

        Returns:
            True if the login and authorization flow completes,
            False otherwise.
        """
        log.info("Starting OAuth login flow in a visible Chrome window…")

        options = Options()
        options.add_argument(f"--user-data-dir={config.CHROME_USER_DATA_DIR}")
        options.add_argument(
            f"--profile-directory={config.CHROME_PROFILE_DIR}"
        )
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        service = Service(executable_path=config.CHROME_DRIVER_PATH)
        try:
            driver = webdriver.Chrome(service=service, options=options)
        except WebDriverException as e:
            log.error(f"Could not launch Chrome for OAuth login: {e}")
            return False

        try:
            target_url = (
                f"https://eagle.ac/game/sdvx/profile/{sdvx_id}"
            )
            driver.get(target_url)

            wait = WebDriverWait(driver, 15)

            try:
                email_fld = wait.until(
                    EC.presence_of_element_located((By.NAME, "email"))
                )
                pass_fld = driver.find_element(By.NAME, "password")
                email_fld.clear()
                email_fld.send_keys(config.EAGLE_EMAIL)
                pass_fld.clear()
                pass_fld.send_keys(config.EAGLE_PASSWORD)
                pass_fld.submit()
                log.info("Submitted Eagle credentials.")
            except TimeoutException:
                log.info(
                    "No login form detected; assuming already "
                    "logged in."
                )

            # Reverted XPath to be more robust, matching original functionality
            auth_btn_xpath = (
                "//button[contains(text(),'Authorize') or "
                "contains(text(),'Allow') or "
                "contains(text(),'approve') or "
                "contains(text(),'Authorize Eagle Bot')]"
            )
            try:
                authorize_btn = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, auth_btn_xpath)
                    )
                )
                authorize_btn.click()
                log.info("Clicked ‘Authorize’ button.")
            except TimeoutException:
                log.info(
                    "No ‘Authorize’ button detected; assuming "
                    "already authorized."
                )

            try:
                wait.until(EC.title_contains("Sound Voltex"))
                log.info("OAuth login complete; session cookie stored.")
            except TimeoutException:
                log.error("Timeout waiting for redirect back to profile.")
                driver.quit()
                return False

            driver.quit()
            return True

        except Exception as e:
            log.error(f"Unexpected error during OAuth login flow: {e}")
            if driver:
                driver.quit()
            return False

    def init_headless_chrome(self) -> bool:
        """
        Initializes a headless ChromeDriver that reuses the stored session.

        This method launches an invisible Chrome instance that uses the
        same user data directory as the OAuth login, allowing it to
        scrape pages as an authenticated user.

        Returns:
            True if the headless driver starts successfully,
            False otherwise.
        """
        log.info("Initializing headless ChromeDriver for scraping…")
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--user-data-dir={config.CHROME_USER_DATA_DIR}")
        options.add_argument(
            f"--profile-directory={config.CHROME_PROFILE_DIR}"
        )

        service = Service(executable_path=config.CHROME_DRIVER_PATH)
        try:
            self.headless_driver = webdriver.Chrome(
                service=service, options=options
            )
            log.info("Headless ChromeDriver initialized successfully.")
            return True
        except WebDriverException as e:
            log.error(
                f"Failed to initialize headless ChromeDriver: {e}"
            )
            return False

    def quit_headless(self):
        """Safely closes the headless browser driver if it is running."""
        if self.headless_driver:
            self.headless_driver.quit()
            self.headless_driver = None
            log.info("Headless ChromeDriver has been quit.")
