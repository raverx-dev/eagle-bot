import os
import asyncio
import logging
from datetime import datetime

import discord
from discord.ext import commands
from dotenv import load_dotenv

from bot import config
from bot.scraper.browser import EagleBrowser
from bot.scraper import parser
from bot.storage import user_manager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Ensure the CHROME_USER_DATA_DIR exists
os.makedirs(config.CHROME_USER_DATA_DIR, exist_ok=True)

# Initialize the browser
BROWSER = EagleBrowser()

# --- Global Data Structures (to be refactored later) ---
# CHECKIN_STORE maps Discord ID (str) to {'vf': int, 'plays': int, 'timestamp': datetime}
CHECKIN_STORE = {}
USER_LINKS = {}

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required for member-related events, if any

bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    """Bot status and initial setup upon connection."""
    log.info(
        f"Bot is online as {bot.user.name}#{bot.user.discriminator}"
    )
    log.info(f"Discord.py version: {discord.__version__}")
    await bot.change_presence(activity=discord.Game(name="SDVX"))

    # Load user links
    global USER_LINKS
    USER_LINKS = user_manager.load_users()
    log.info(f"Loaded user links: {USER_LINKS}")

    # Note: headless Chrome will be initialized when needed after OAuth


# --- Discord Commands ---
@bot.command(
    name="linkid",
    help="Link your Discord account to SDVX ID (Admin)"
)
@commands.has_permissions(administrator=True)
async def linkid(ctx, sdvx_id: str):
    """
    Links a user's Discord account to their SDVX ID.
    Usage: /linkid <SDVX_ID>
    """
    discord_id = str(ctx.author.id)
    sdvx_id_clean = sdvx_id.replace("-", "")

    if not sdvx_id_clean.isdigit():
        await ctx.send(
            "Error: SDVX ID must be numeric, even with hyphens."
        )
        return

    await ctx.send(
        "Starting OAuth login... Please approve the browser window."
    )
    login_success = await asyncio.to_thread(
        BROWSER.run_oauth_login,
        sdvx_id_clean,
    )

    if not login_success:
        await ctx.send(
            "Failed to perform OAuth login with the provided SDVX ID. "
            "Please ensure it's correct and approve the browser window."
        )
        return

    global USER_LINKS
    USER_LINKS[discord_id] = sdvx_id_clean
    user_manager.save_users(USER_LINKS)
    await ctx.send(
        f"Successfully linked Discord user `{ctx.author.display_name}` "
        f"to SDVX ID `{sdvx_id_clean}`. OAuth login completed "
        f"and cookie saved."
    )
    log.info(f"Linked {ctx.author.id} to {sdvx_id_clean}")

    # Now initialize headless Chrome for scraping
    if not BROWSER.init_headless_chrome():
        await ctx.send(
            "Warning: Headless browser initialization failed. "
            "Scraping commands may not work."
        )
        log.error(
            "Headless browser initialization failed after OAuth."
        )
    else:
        await ctx.send(
            "Headless browser is now ready for scraping."
        )
        log.info(
            "Headless browser initialized successfully after OAuth."
        )


@linkid.error
async def linkid_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "Usage: `/linkid <SDVX_ID>`. Please provide an SDVX ID."
        )
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "You don't have permission to use this command."
        )
    else:
        log.error(f"Error in linkid command: {error}")
        await ctx.send(f"An unexpected error occurred: {error}")


@bot.command(
    name="stats",
    help="Displays your current SDVX stats."
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
            "Please use `/linkid <SDVX_ID>`."
        )
        return

    if not BROWSER.headless_driver:
        if not BROWSER.init_headless_chrome():
            await ctx.send(
                "Error: Headless browser not initialized. "
                "Cannot fetch stats."
            )
            log.error(
                "Headless browser could not be initialized for /stats."
            )
            return

    await ctx.send(f"Fetching stats for SDVX ID `{sdvx_id}`...")

    current_vf = parser.get_vf_from_arcade(
        BROWSER.headless_driver,
        sdvx_id,
    )
    profile_data = parser.scrape_profile_page(
        BROWSER.headless_driver,
        sdvx_id,
    )
    if not profile_data:
        await ctx.send(
            "Could not retrieve profile data. Site may be down "
            "or your ID is incorrect."
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
            f"• {title} {difficulty} {level} "
            f"PLAYED {score} ({time_ago})"
        )

    response = (
        f"**__Your SDVX Stats:__**\n"
        f"**Volforce:** `{current_vf}`\n"
        f"**Skill Level:** `{skill_level}`\n"
        f"**Total Plays:** `{total_plays}`\n"
        f"**Last 5 Plays:**\n"
        + (
            "\n".join(formatted_plays)
            if formatted_plays
            else "  No recent plays found."
        )
    )
    await ctx.send(response)


@bot.command(
    name="leaderboard",
    help="Displays the top 10 players on the arcade leaderboard."
)
async def leaderboard(ctx):
    """
    Displays the top-10 ranked players from the arcade's VF leaderboard,
    showing rank, name, and VF.
    """
    if not BROWSER.headless_driver:
        if not BROWSER.init_headless_chrome():
            await ctx.send(
                "Error: Headless browser not initialized. "
                "Cannot fetch leaderboard."
            )
            log.error(
                "Headless browser could not be initialized for "
                "/leaderboard."
            )
            return

    await ctx.send(
        "Fetching leaderboard data. This might take a moment..."
    )

    leaderboard_data = parser.scrape_leaderboard(
        BROWSER.headless_driver
    )
    if not leaderboard_data:
        await ctx.send(
            "Could not retrieve leaderboard data. The website might be down."
        )
        return

    response = "**__Arcade Top 10 Volforce Leaderboard:__**\n"
    for player in leaderboard_data:
        response += (
            f"**Rank {player['rank']}**: {player['name']} "
            f"— `{player['vf']} VF`\n"
        )
    await ctx.send(response)


@bot.command(
    name="checkin",
    help="Records your current VF and play count for a session."
)
async def checkin(ctx):
    """
    Records a user's current VF and play count as the start of a session.
    """
    discord_id = str(ctx.author.id)
    sdvx_id = USER_LINKS.get(discord_id)

    if not sdvx_id:
        await ctx.send(
            "Your Discord account is not linked to an SDVX ID. "
            "Please use `/linkid <SDVX_ID>`."
        )
        return

    if not BROWSER.headless_driver:
        if not BROWSER.init_headless_chrome():
            await ctx.send(
                "Error: Headless browser not initialized. Cannot check in."
            )
            log.error(
                "Headless browser could not be initialized for /checkin."
            )
            return

    current_vf = parser.get_vf_from_arcade(
        BROWSER.headless_driver,
        sdvx_id,
    )
    profile_data = parser.scrape_profile_page(
        BROWSER.headless_driver,
        sdvx_id,
    )
    current_plays = profile_data.get("total_plays", 0)

    CHECKIN_STORE[discord_id] = {
        'vf': current_vf,
        'plays': current_plays,
        'timestamp': datetime.now(),
    }
    await ctx.send(
        f"Checked in! Your current VF is `{current_vf}` and "
        f"plays are `{current_plays}`. Use `/checkout` to see stats."
    )
    log.info(
        f"User {discord_id} checked in with VF {current_vf} "
        f"and plays {current_plays}."
    )


@bot.command(
    name="checkout",
    help="Compares current stats to your last check-in."
)
async def checkout(ctx):
    """
    Compares current stats to the last check-in and shows VF gained,
    plays gained, and session duration.
    """
    discord_id = str(ctx.author.id)

    if discord_id not in CHECKIN_STORE:
        await ctx.send("You haven't checked in yet! Use `/checkin` first.")
        return

    checkin_data = CHECKIN_STORE[discord_id]
    sdvx_id = USER_LINKS.get(discord_id)

    if not sdvx_id:
        await ctx.send(
            "Your Discord account is not linked to an SDVX ID. "
            "Please use `/linkid <SDVX_ID>`."
        )
        return

    if not BROWSER.headless_driver:
        if not BROWSER.init_headless_chrome():
            await ctx.send(
                "Error: Headless browser not initialized. Cannot check out."
            )
            log.error(
                "Headless browser could not be initialized for /checkout."
            )
            return

    await ctx.send("Fetching current stats for checkout...")

    current_vf = parser.get_vf_from_arcade(
        BROWSER.headless_driver,
        sdvx_id,
    )
    profile_data = parser.scrape_profile_page(
        BROWSER.headless_driver,
        sdvx_id,
    )
    current_plays = profile_data.get("total_plays", 0)

    vf_gained = current_vf - checkin_data['vf']
    plays_gained = current_plays - checkin_data['plays']
    session_duration = datetime.now() - checkin_data['timestamp']

    # Format duration
    days, seconds = session_duration.days, session_duration.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if days > 0:
        duration_str = f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        duration_str = f"{hours}h {minutes}m"
    else:
        duration_str = (
            f"{minutes}m" if minutes > 0 else "less than a minute"
        )

    response = (
        f"**__Session Summary:__**\n"
        f"**Check-in VF:** `{checkin_data['vf']}`\n"
        f"**Current VF:** `{current_vf}`\n"
        f"**VF Gained:** `{vf_gained}`\n"
        f"**Check-in Plays:** `{checkin_data['plays']}`\n"
        f"**Current Plays:** `{current_plays}`\n"
        f"**Plays Gained:** `{plays_gained}`\n"
        f"**Session Duration:** `{duration_str}`"
    )
    await ctx.send(response)
    log.info(
        f"User {discord_id} checked out. VF Gained: {vf_gained}, "
        f"Plays Gained: {plays_gained}."
    )

    del CHECKIN_STORE[discord_id]


# --- Run the Bot ---
if __name__ == "__main__":
    discord_token = os.getenv("DISCORD_TOKEN")
    if discord_token is None:
        log.error("DISCORD_TOKEN environment variable not set. Exiting.")
        exit(1)

    try:
        bot.run(discord_token)
    except discord.errors.LoginFailure as e:
        log.error(
            f"Failed to log in to Discord: {e}. "
            "Please check your DISCORD_TOKEN."
        )
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}")
    finally:
        BROWSER.quit_headless()
        log.info("Bot process finished.")
