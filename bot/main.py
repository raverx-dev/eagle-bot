import os
import json
import logging
from datetime import datetime

import discord
from discord.ext import commands
from dotenv import load_dotenv

from bot import config
from bot.scraper.browser import EagleBrowser
from bot.scraper import parser

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Ensure the CHROME_USER_DATA_DIR exists
os.makedirs(config.CHROME_USER_DATA_DIR, exist_ok=True)

# Initialize the browser
BROWSER = EagleBrowser()

# --- Global Data Structures (to be refactored later) ---
USER_LINKS_FILE = "watched_players.json"
USER_LINKS = {}  # Discord ID (str) -> SDVX ID (str)

# Discord ID (str) -> {'vf': int, 'plays': int, 'timestamp': datetime}
CHECKIN_STORE = {}

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required for member-related events

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """Bot status and initial setup upon connection."""
    log.info(
        f"Bot is online as {bot.user.name}#{bot.user.discriminator}"
    )
    log.info(f"Discord.py version: {discord.__version__}")
    await bot.change_presence(activity=discord.Game(name="SDVX"))

    # Initial login for cookie persistence
    if not BROWSER.init_headless_chrome():
        log.error(
            "Failed to initialize headless browser. "
            "Commands may not work."
        )
    else:
        log.info(
            "Headless browser successfully initialized for scraping."
        )

    # Load user links
    load_user_links()
    log.info(f"Loaded user links: {USER_LINKS}")


# --- User Link Management ---
def load_user_links():
    """Loads Discord-SDVX ID links from the JSON file."""
    if os.path.exists(USER_LINKS_FILE):
        try:
            with open(USER_LINKS_FILE, "r") as f:
                USER_LINKS.update(json.load(f))
        except json.JSONDecodeError as e:
            log.error(f"Error loading {USER_LINKS_FILE}: {e}")
            USER_LINKS.clear()
    else:
        log.info(
            f"{USER_LINKS_FILE} not found. Starting with empty links."
        )
        with open(USER_LINKS_FILE, "w") as f:
            json.dump({}, f)


def save_user_links():
    """Saves Discord-SDVX ID links to the JSON file."""
    try:
        with open(USER_LINKS_FILE, "w") as f:
            json.dump(USER_LINKS, f, indent=4)
    except IOError as e:
        log.error(f"Error saving {USER_LINKS_FILE}: {e}")


# --- Discord Commands ---
@bot.command(
    name="linkid",
    help="Links your Discord account to an SDVX ID (Admin Only).",
)
@commands.has_permissions(administrator=True)
async def linkid(ctx, sdvx_id: str):
    """
    Links a user's Discord account to their SDVX ID.
    Usage: !linkid <SDVX_ID>
    """
    discord_id = str(ctx.author.id)
    sdvx_id_clean = sdvx_id.replace("-", "")

    if not sdvx_id_clean.isdigit():
        await ctx.send(
            "Error: SDVX ID must be numeric, even with hyphens."
        )
        return

    # Try to perform OAuth login using the provided ID.
    if not BROWSER.run_oauth_login(sdvx_id_clean):
        await ctx.send(
            "Failed to perform OAuth login with the provided SDVX ID. "
            "Please ensure it's correct."
        )
        return

    USER_LINKS[discord_id] = sdvx_id_clean
    save_user_links()
    await ctx.send(
        f"Successfully linked Discord user "
        f"`{ctx.author.display_name}` to SDVX ID "
        f"`{sdvx_id_clean}`. OAuth login completed and cookie saved."
    )
    log.info(f"Linked {ctx.author.id} to {sdvx_id_clean}")


@linkid.error
async def linkid_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "Usage: `!linkid <SDVX_ID>`. Please provide an SDVX ID."
        )
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    else:
        log.error(f"Error in linkid command: {error}")
        await ctx.send(f"An unexpected error occurred: {error}")


@bot.command(
    name="stats",
    help="Displays your current SDVX stats.",
)
async def stats(ctx):
    """
    Displays the linked user's current Volforce (VF), Skill Level,
    total play count, and last 5 plays.
    """
    discord_id = str(ctx.author.id)
    sdvx_id = USER_LINKS.get(discord_id)

    if not sdvx_id:
        await ctx.send(
            "Your Discord account is not linked to an SDVX ID. "
            "Please use `!linkid <SDVX_ID>`."
        )
        return

    await ctx.send(f"Fetching stats for SDVX ID `{sdvx_id}`...")

    current_vf = parser.get_vf_from_arcade(
        BROWSER.headless_driver, sdvx_id
    )
    profile_data = parser.scrape_profile_page(
        BROWSER.headless_driver, sdvx_id
    )
    if not profile_data:
        await ctx.send(
            "Could not retrieve profile data. The website might "
            "be down or your ID is incorrect."
        )
        return

    skill_level = profile_data.get("skill_level", "N/A")
    total_plays = profile_data.get("total_plays", "N/A")
    last_5_plays = profile_data.get("last_5_plays", [])

    # Format last 5 plays
    formatted_plays = []
    for play in last_5_plays:
        title = play.get("title", "Unknown Title")
        difficulty = play.get("difficulty", "N/A")
        level = play.get("level", "N/A")
        score = play.get("score", "N/A")
        time_ago = play.get("time_ago", "N/A")
        formatted_plays.append(
            f"• {title} {difficulty} {level} PLAYED {score} ({time_ago})"
        )

    response = (
        "**__Your SDVX Stats:__**\n"
        f"**Volforce:** `{current_vf}`\n"
        f"**Skill Level:** `{skill_level}`\n"
        f"**Total Plays:** `{total_plays}`\n"
        "**Last 5 Plays:**\n" +
        ("\n".join(formatted_plays) if formatted_plays else
         "  No recent plays found.")
    )
    await ctx.send(response)


@bot.command(
    name="leaderboard",
    help="Displays the top 10 players on the arcade leaderboard.",
)
async def leaderboard(ctx):
    """
    Displays the top-10 ranked players from the arcade's VF leaderboard,
    showing rank, name, and VF.
    """
    await ctx.send("Fetching leaderboard data. This might take a moment...")

    leaderboard_data = parser.scrape_leaderboard(
        BROWSER.headless_driver
    )
    if not leaderboard_data:
        await ctx.send(
            "Could not retrieve leaderboard data. "
            "The website might be down."
        )
        return

    response = "**__Arcade Top 10 Volforce Leaderboard:__**\n"
    for player in leaderboard_data:
        response += (
            f"**Rank {player['rank']}**: {player['name']} — "
            f"`{player['vf']} VF`\n"
        )
    await ctx.send(response)


@bot.command(
    name="checkin",
    help="Records your current VF and play count for a session.",
)
async def checkin(ctx):
    """
    Records a user's current VF and play count as the start
    of a session.
    """
    discord_id = str(ctx.author.id)
    sdvx_id = USER_LINKS.get(discord_id)

    if not sdvx_id:
        await ctx.send(
            "Your Discord account is not linked to an SDVX ID. "
            "Please use `!linkid <SDVX_ID>`."
        )
        return

    current_vf = parser.get_vf_from_arcade(
        BROWSER.headless_driver, sdvx_id
    )
    profile_data = parser.scrape_profile_page(
        BROWSER.headless_driver, sdvx_id
    )
    current_plays = profile_data.get("total_plays", 0)

    CHECKIN_STORE[discord_id] = {
        "vf": current_vf,
        "plays": current_plays,
        "timestamp": datetime.now(),
    }
    await ctx.send(
        f"Checked in! Your current VF is `{current_vf}` and plays are "
        f"`{current_plays}`. Use `!checkout` to see session stats."
    )
    log.info(
        f"User {discord_id} checked in with VF {current_vf} and "
        f"plays {current_plays}."
    )
