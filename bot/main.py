# ──────────────────────────────────────────────────────────────────────────────
# FILE: bot/main.py
# ──────────────────────────────────────────────────────────────────────────────

import os
import threading
import datetime
import asyncio
import logging

import discord
from discord.ext import commands

from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Selenium imports (for both headed OAuth automation & headless scraping)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# ──────────────────────────────────────────────────────────────────────────────
#  Load environment variables
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
if not DISCORD_BOT_TOKEN:
    raise RuntimeError("You must set DISCORD_BOT_TOKEN in .env")

EAGLE_EMAIL    = os.getenv("EAGLE_EMAIL", "").strip()
EAGLE_PASSWORD = os.getenv("EAGLE_PASSWORD", "").strip()
if not (EAGLE_EMAIL and EAGLE_PASSWORD):
    raise RuntimeError("You must set EAGLE_EMAIL and EAGLE_PASSWORD in .env")

# ──────────────────────────────────────────────────────────────────────────────
#  Paths to ChromeDriver & Chrome user‐data
# ──────────────────────────────────────────────────────────────────────────────
CHROME_DRIVER_PATH = "/usr/bin/chromedriver"  # Adjust if your chromedriver lives elsewhere

# We will store (and later reuse) the “logged-in” Eagle session cookie here:
CHROME_USER_DATA_DIR = os.path.expanduser("~/.selenium_profiles/eaglebot_profile")
CHROME_PROFILE_DIR   = "Default"

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
#  Admins must run !linkid once per Discord user to populate this.
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
                pass_fld  = driver.find_element(By.NAME, "password")
                email_fld.clear()
                email_fld.send_keys(EAGLE_EMAIL)
                pass_fld.clear()
                pass_fld.send_keys(EAGLE_PASSWORD)
                pass_fld.submit()
                log.info("✅ Submitted Eagle credentials.")
            except TimeoutException:
                # Possibly already logged in to kailua/eagle or no login form shown.
                log.info("ℹ️  No login form detected; assuming already logged into kailua/eagle.")

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
                log.info("ℹ️  No ‘Authorize’ button detected; maybe already authorized previously.")

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
        log.info("☁️  Initializing headless ChromeDriver for scraping…")
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

# ──────────────────────────────────────────────────────────────────────────────
#  Helper: parse raw HTML into BeautifulSoup
# ──────────────────────────────────────────────────────────────────────────────
def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


# ──────────────────────────────────────────────────────────────────────────────
#  Scrape a player’s profile page for Skill, Plays, Packet, Block.
# ──────────────────────────────────────────────────────────────────────────────
def scrape_profile_page(sdvx_id: str) -> dict:
    """
    Visit https://eagle.ac/game/sdvx/profile/{sdvx_id} using headless Chrome,
    and return a dict with keys: { 'skill', 'plays', 'packet', 'block' }.
    """
    result = {
        "skill": "—",
        "plays": "—",
        "packet": "—",
        "block": "—",
    }

    url = f"https://eagle.ac/game/sdvx/profile/{sdvx_id}"
    driver = BROWSER.headless_driver
    driver.get(url)
    driver.implicitly_wait(5)

    html = driver.page_source
    soup = parse_html(html)

    # The stats are in the right-hand sidebar, inside <ul class="list-group">
    sidebar_ul = soup.find("ul", {"class": "list-group"})
    if not sidebar_ul:
        return result

    for li in sidebar_ul.find_all("li", class_="list-group-item"):
        text = li.get_text(separator=" ", strip=True)
        # Skill Level
        if text.startswith("Skill Level:"):
            try:
                skill_text = text.split("for")[0].replace("Skill Level:", "").strip()
                result["skill"] = skill_text
            except:
                pass
        # Plays
        elif text.startswith("Plays:"):
            try:
                plays_val = text.replace("Plays:", "").strip().replace(",", "")
                result["plays"] = plays_val
            except:
                pass
        # Packet / Block
        elif text.startswith("Packet:"):
            try:
                parts = text.replace("Packet:", "").split("Block:")
                packet_val = parts[0].strip().split()[0].replace(",", "")
                block_val = parts[1].strip().split()[0].replace(",", "")
                result["packet"] = packet_val
                result["block"] = block_val
            except:
                pass

    return result


# ──────────────────────────────────────────────────────────────────────────────
#  Scrape the arcade leaderboard (top 10) from https://eagle.ac/arcade/{arcade_id}.
# ──────────────────────────────────────────────────────────────────────────────
def scrape_leaderboard(arcade_id: str) -> list:
    """
    Returns a list of dicts for the top 10:
    [ { "rank": "1", "sdvx_id": "1266-6165", "name": "#-FINN-#", "vf": "17.020" }, ... ]
    """
    driver = BROWSER.headless_driver
    url = f"https://eagle.ac/arcade/{arcade_id}"
    driver.get(url)
    driver.implicitly_wait(5)

    html = driver.page_source
    soup = parse_html(html)

    # Find the <h3 class="panel-title">Sound Voltex - Arcade Top 10</h3>
    h3 = soup.find("h3", class_="panel-title", string=lambda t: t and "Arcade Top 10" in t)
    if not h3:
        return []

    # The panel containing that heading has class "panel panel-primary"
    panel_div = h3.find_parent("div", class_="panel-primary")
    if not panel_div:
        return []

    # Inside that panel, find the <table> for the leaderboard
    lead_table = panel_div.find("table", {"class": "table"})
    if not lead_table:
        return []

    output = []
    for row in lead_table.select("tbody > tr"):
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        rank    = cols[0].get_text(strip=True)
        sdvx_id = cols[1].get_text(strip=True)
        name    = cols[2].get_text(strip=True)
        vf_val  = cols[3].get_text(strip=True)
        output.append({
            "rank": rank,
            "sdvx_id": sdvx_id,
            "name": name,
            "vf": vf_val,
        })
    return output


# ──────────────────────────────────────────────────────────────────────────────
#  Utility: Look up a single player's VF in the Arcade Top 10 by comparing IDs
# ──────────────────────────────────────────────────────────────────────────────
def get_vf_from_arcade(sdvx_id: str) -> str:
    """
    Given an SDVX ID without hyphens (e.g. "95688187"), attempt to find that
    player in the Arcade Top 10 and return their VF. If not found, return "—".
    """
    board = scrape_leaderboard(ARCADE_ID)
    for entry in board:
        # entry["sdvx_id"] has hyphens, e.g. "9568-8187"
        if entry["sdvx_id"].replace("-", "") == sdvx_id:
            return entry["vf"]
    return "—"


# ──────────────────────────────────────────────────────────────────────────────
#  DISCORD BOT SETUP (prefix commands)
# ──────────────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    log.info(f"Bot is online as {bot.user} (ID {bot.user.id})")

    if not USER_LINKS:
        log.warning("⚠️ No users linked (USER_LINKS is empty). Skipping OAuth login. Please run /linkid for at least one user and restart the bot.")
        return

    first_sdvx = next(iter(USER_LINKS.values()))
    loop = asyncio.get_event_loop()

    login_success = await loop.run_in_executor(None, BROWSER.run_oauth_login, first_sdvx)
    if not login_success:
        log.error("❌ OAuth login automation failed. The bot will not be able to scrape without a valid eagle.ac cookie.")
        return

    headless_success = await loop.run_in_executor(None, BROWSER.init_headless_chrome)
    if not headless_success:
        log.error("❌ Headless ChromeDriver initialization failed. Scraping commands will not work.")
    else:
        log.info("✅ Headless ChromeDriver is ready (authenticated).")


# ──────────────────────────────────────────────────────────────────────────────
#  !linkid (Admin only) → map a Discord user → SDVX ID
# ──────────────────────────────────────────────────────────────────────────────
@bot.command(name="linkid")
@commands.has_permissions(administrator=True)
async def linkid(ctx: commands.Context, sdvx_id: str):
    """
    Usage (admin only): /linkid 95688187
    Saves your Discord user → SDVX ID mapping.
    """
    cleaned = sdvx_id.strip()
    USER_LINKS[ctx.author.id] = cleaned
    await ctx.send(f"✅ Saved your SDVX ID as **{cleaned}**. Now initializing OAuth & headless Chrome…")

    loop = asyncio.get_event_loop()
    login_success = await loop.run_in_executor(None, BROWSER.run_oauth_login, cleaned)
    if not login_success:
        await ctx.send("❌ OAuth login flow failed. Please check your Eagle credentials or rerun /linkid.")
        return

    headless_success = await loop.run_in_executor(None, BROWSER.init_headless_chrome)
    if not headless_success:
        await ctx.send("❌ Headless ChromeDriver initialization failed. Scraping commands will not work.")
    else:
        await ctx.send("✅ Headless ChromeDriver is ready. You may now use /checkin, /stats, /leaderboard.")


# ──────────────────────────────────────────────────────────────────────────────
#  !stats → display Skill/Plays/Packet/Block/VF for the invoking user
# ──────────────────────────────────────────────────────────────────────────────
@bot.command(name="stats")
async def stats(ctx: commands.Context):
    user_id = ctx.author.id
    if user_id not in USER_LINKS:
        await ctx.send("⚠️ You have not linked Eagle yet. An admin must run `/linkid` for you.")
        return

    sdvx_id = USER_LINKS[user_id]
    await ctx.send("🔄 Fetching your SDVX profile… Please wait a moment.")

    data = scrape_profile_page(sdvx_id)
    vf_val = get_vf_from_arcade(sdvx_id)

    embed = discord.Embed(
        title=f"📊 Stats for {ctx.author.display_name} ({sdvx_id})",
        color=discord.Color.blue()
    )
    embed.add_field(name="Skill Level",    value=data.get("skill", "—"), inline=True)
    embed.add_field(name="Total Plays",    value=data.get("plays", "—"), inline=True)
    embed.add_field(name="Packet",         value=data.get("packet", "—"), inline=True)
    embed.add_field(name="Block",          value=data.get("block", "—"), inline=True)
    embed.add_field(name="Volforce (VF)",  value=vf_val, inline=False)

    await ctx.send(embed=embed)


# ──────────────────────────────────────────────────────────────────────────────
#  !checkin → same as !stats but with a green “Checked In” heading
# ──────────────────────────────────────────────────────────────────────────────
@bot.command(name="checkin")
async def checkin(ctx: commands.Context):
    user_id = ctx.author.id
    if user_id not in USER_LINKS:
        await ctx.send("⚠️ You have not linked Eagle yet. An admin must run `/linkid` for you.")
        return

    sdvx_id = USER_LINKS[user_id]
    await ctx.send("✅ Checked In. Fetching your data…")

    data = scrape_profile_page(sdvx_id)
    vf_val = get_vf_from_arcade(sdvx_id)

    embed = discord.Embed(
        title="✅ Checked In",
        description=(
            f"SDVX ID {sdvx_id}  •  Skill Level {data.get('skill','—')}  •  Total Plays {data.get('plays','—')}  •  VF {vf_val}"
        ),
        color=discord.Color.green()
    )

    try:
        plays_val = int(data.get("plays", "0"))
    except:
        plays_val = 0

    try:
        vf_float = float(vf_val) if vf_val != "—" else 0.0
    except:
        vf_float = 0.0

    CHECKIN_STORE[user_id] = {
        "time": datetime.datetime.now(datetime.timezone.utc),
        "plays": plays_val,
        "vf": vf_float
    }

    await ctx.send(embed=embed)


# ──────────────────────────────────────────────────────────────────────────────
#  !checkout → compare to last check‐in, show Plays & VF gained + duration
# ──────────────────────────────────────────────────────────────────────────────
CHECKIN_STORE = {}  # { discord_user_id: { "time": datetime, "plays": int, "vf": float } }

@bot.command(name="checkout")
async def checkout(ctx: commands.Context):
    user_id = ctx.author.id
    if user_id not in USER_LINKS:
        await ctx.send("⚠️ You have not linked Eagle yet. An admin must run `/linkid` for you.")
        return

    if user_id not in CHECKIN_STORE:
        await ctx.send("⚠️ You have not checked in yet. Use `/checkin` first.")
        return

    sdvx_id = USER_LINKS[user_id]
    await ctx.send("🏁 Checking out… Fetching your current stats…")

    data = scrape_profile_page(sdvx_id)
    vf_val_now = get_vf_from_arcade(sdvx_id)

    try:
        current_plays = int(data.get("plays", "0"))
    except:
        current_plays = 0

    try:
        current_vf = float(vf_val_now) if vf_val_now != "—" else 0.0
    except:
        current_vf = 0.0

    old = CHECKIN_STORE[user_id]
    elapsed = datetime.datetime.now(datetime.timezone.utc) - old["time"]
    plays_gained = current_plays - old["plays"]
    vf_gained = current_vf - old["vf"]

    embed = discord.Embed(
        title="🏁 Checked Out",
        description=(
            f"Plays at Check‐in {old['plays']}  •  Plays Now {current_plays}  •  Plays Gained {plays_gained}\n"
            f"VF at Check‐in {old['vf']:.3f}  •  VF Now {current_vf:.3f}  •  VF Gained {vf_gained:.3f}\n"
            f"Session Duration {str(elapsed).split('.')[0]}"
        ),
        color=discord.Color.blue()
    )
    del CHECKIN_STORE[user_id]
    await ctx.send(embed=embed)


# ──────────────────────────────────────────────────────────────────────────────
#  !leaderboard → show the arcade’s Top‐10 VF leaderboard (Arcade #94 by default)
# ──────────────────────────────────────────────────────────────────────────────
ARCADE_ID = "94"  # ← change to your own arcade number if it’s different

@bot.command(name="leaderboard")
async def leaderboard(ctx: commands.Context):
    await ctx.send("🔄 Fetching Arcade Top-10 VF leaderboard…")
    board = scrape_leaderboard(ARCADE_ID)
    if not board:
        await ctx.send("⚠️ Could not find the ‘Arcade Top 10’ table on eagle.ac.")
        return

    lines = []
    for entry in board:
        lines.append(f"**{entry['rank']}.**  {entry['name']}  (`{entry['sdvx_id']}`) — {entry['vf']} VF")

    embed = discord.Embed(
        title="🏆 Electric Starship Arcade – SDVX Top 10",
        description="\n".join(lines),
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)


# ──────────────────────────────────────────────────────────────────────────────
#  Run the bot
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
