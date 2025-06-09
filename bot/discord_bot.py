import discord
from discord.ext import commands
import asyncio
import os
import sys
import datetime 

# Add the parent directory to the Python path to allow imports from 'bot' package
# This is crucial for running the bot correctly from the project root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.config import log, OAUTH_LOGIN_ENABLED
from bot.eagle_browser import BROWSER
from bot.scraper import scrape_profile_page, get_vf_from_arcade, scrape_leaderboard
from bot.checkin_store import USER_LINKS, CHECKIN_STORE, load_linked_players, save_linked_players

# ──────────────────────────────────────────────────────────────────────────────
# Discord Bot Setup
# ──────────────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True # Required for accessing message.content
bot = commands.Bot(command_prefix='!', intents=intents)

# ──────────────────────────────────────────────────────────────────────────────
# Bot Events
# ──────────────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    """
    Event that fires when the bot has successfully connected to Discord.
    It logs the bot's readiness and performs initial setup tasks like
    loading persistent data and potentially initiating OAuth login.
    """
    log.info(f"Bot is online as {bot.user} (ID {bot.user.id})")

    # Load linked players from persistent storage when bot is ready
    log.info("DISCORD_BOT: Attempting to load USER_LINKS from checkin_store in on_ready.")
    loaded_users = load_linked_players()
    USER_LINKS.update(loaded_users)
    log.info(f"DISCORD_BOT: USER_LINKS updated with {len(USER_LINKS)} entries in on_ready.")

    # Only attempt OAuth login if users are linked and OAUTH_LOGIN_ENABLED is True
    if USER_LINKS and OAUTH_LOGIN_ENABLED:
        log.info("DISCORD_BOT: Linked users found and OAuth login enabled. Starting OAuth login flow.")
        try:
            # Get the first linked SDVX ID to pass to run_oauth_login
            # This uses a linked ID as per the status report's root cause analysis.
            first_sdvx_id = next(iter(USER_LINKS.values()), None)
            if first_sdvx_id:
                await BROWSER.run_oauth_login(first_sdvx_id)
                log.info("DISCORD_BOT: OAuth login automation completed successfully.")
            else:
                log.warning("DISCORD_BOT: USER_LINKS is not empty but no SDVX ID found to use for OAuth. Skipping OAuth login.")
        except Exception as e:
            log.error(f"DISCORD_BOT: OAuth login automation failed: {e}")
            log.warning("DISCORD_BOT: The bot will not be able to scrape without a valid eagle.ac cookie.")
    else:
        if not USER_LINKS:
            log.warning("DISCORD_BOT: ⚠️ No users linked (USER_LINKS is empty). Skipping OAuth login. Please run /linkid for at least one user and restart the bot.")
        elif not OAUTH_LOGIN_ENABLED:
            log.info("DISCORD_BOT: OAuth login explicitly disabled in config. Skipping OAuth login.")


# ──────────────────────────────────────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────────────────────────────────────
@bot.command(name='linkid')
async def link_id(ctx, sdvx_id: str):
    """
    Links a Discord user to their SDVX ID.
    Usage: !linkid <sdvx_id>
    """
    discord_user_id = ctx.author.id
    USER_LINKS[discord_user_id] = sdvx_id
    save_linked_players(USER_LINKS) # Save changes to persistent storage
    await ctx.send(f"Successfully linked {ctx.author.display_name} to SDVX ID: {sdvx_id}")
    log.info(f"Linked Discord user {discord_user_id} to SDVX ID {sdvx_id}")

@bot.command(name='checkin')
async def checkin(ctx):
    """
    Manually checks a user into the arcade tracking system.
    Usage: !checkin
    """
    discord_user_id = ctx.author.id
    if discord_user_id not in USER_LINKS:
        await ctx.send("You need to link your SDVX ID first using !linkid <your_sdvx_id>.")
        return

    sdvx_id = USER_LINKS[discord_user_id]
    
    # Placeholder for actual check-in logic
    # In a real scenario, this would trigger scraping to get initial stats
    # and set up a session.
    CHECKIN_STORE[discord_user_id] = {
        "time": datetime.datetime.now(),
        "plays": 0, # Placeholder
        "vf": 0.0    # Placeholder
    }
    await ctx.send(f"Checked in {ctx.author.display_name} (SDVX ID: {sdvx_id}).")
    log.info(f"User {discord_user_id} checked in.")

@bot.command(name='checkout')
async def checkout(ctx):
    """
    Manually checks a user out of the arcade tracking system.
    Usage: !checkout
    """
    discord_user_id = ctx.author.id
    if discord_user_id in CHECKIN_STORE:
        session_info = CHECKIN_STORE.pop(discord_user_id)
        duration = datetime.datetime.now() - session_info["time"]
        await ctx.send(f"Checked out {ctx.author.display_name}. Session lasted {duration}.")
        log.info(f"User {discord_user_id} checked out.")
    else:
        await ctx.send("You are not currently checked in.")

@bot.command(name='stats')
async def show_stats(ctx):
    """
    Displays current stats for the linked SDVX ID.
    Usage: !stats
    """
    discord_user_id = ctx.author.id
    if discord_user_id not in USER_LINKS:
        await ctx.send("You need to link your SDVX ID first using !linkid <your_sdvx_id>.")
        return

    sdvx_id = USER_LINKS[discord_user_id]
    await ctx.send(f"Fetching stats for SDVX ID: {sdvx_id}...")
    
    try:
        # This is a placeholder for actual scraping of stats
        # In a real scenario, this would use the BROWSER to get current stats
        profile_data = scrape_profile_page(BROWSER, sdvx_id)
        vf = get_vf_from_arcade(BROWSER, sdvx_id) # Example usage
        await ctx.send(f"Current VF for {sdvx_id}: {vf} (Profile: {profile_data})")
        log.info(f"Fetched stats for {sdvx_id}")
    except Exception as e:
        await ctx.send(f"Could not fetch stats for {sdvx_id}. Error: {e}")
        log.error(f"Failed to fetch stats for {sdvx_id}: {e}")

@bot.command(name='leaderboard')
async def show_leaderboard(ctx):
    """
    Displays the current top 10 arcade leaderboard.
    Usage: !leaderboard
    """
    await ctx.send("Fetching leaderboard...")
    try:
        leaderboard_data = scrape_leaderboard(BROWSER)
        formatted_leaderboard = "\n".join([f"{i+1}. {p['name']} ({p['vf']})" for i, p in enumerate(leaderboard_data)])
        await ctx.send(f"**Arcade Leaderboard Top 10:**\n{formatted_leaderboard}")
        log.info("Fetched leaderboard.")
    except Exception as e:
        await ctx.send(f"Could not fetch leaderboard. Error: {e}")
        log.error(f"Failed to fetch leaderboard: {e}")
