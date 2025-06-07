# ──────────────────────────────────────────────────────────────────────────────
# FILE: bot/scraper.py
# ──────────────────────────────────────────────────────────────────────────────

from bs4 import BeautifulSoup

# Import the BROWSER instance from eagle_browser module
from bot.eagle_browser import BROWSER
# Import ARCADE_ID from config module
from bot.config import ARCADE_ID

# ──────────────────────────────────────────────────────────────────────────────
# Helper: parse raw HTML into BeautifulSoup
# ──────────────────────────────────────────────────────────────────────────────
def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


# ──────────────────────────────────────────────────────────────────────────────
# Scrape a player’s profile page for Skill, Plays, Packet, Block.
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
# Scrape the arcade leaderboard (top 10) from https://eagle.ac/arcade/{arcade_id}.
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
        rank = cols[0].get_text(strip=True)
        sdvx_id = cols[1].get_text(strip=True)
        name = cols[2].get_text(strip=True)
        vf_val = cols[3].get_text(strip=True)
        output.append({
            "rank": rank,
            "sdvx_id": sdvx_id,
            "name": name,
            "vf": vf_val,
        })
    return output


# ──────────────────────────────────────────────────────────────────────────────
# Utility: Look up a single player's VF in the Arcade Top 10 by comparing IDs
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
