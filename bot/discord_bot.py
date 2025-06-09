import os
import discord
from discord.ext import commands
from bot.config import log, DISCORD_BOT_TOKEN
from bot.eagle_browser import BROWSER
from bot.scraper import scrape_profile_page, get_vf_from_arcade, scrape_leaderboard
from bot.checkin_store import CHECKIN_STORE, USER_LINKS, load_linked_players, save_linked_players

# ──────────────────────────────────────────────────────────────────────────────
# Discord Bot Setup
# ──────────────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True # Required for member-related events like role/nickname changes

bot = commands.Bot(command_prefix="!", intents=intents)

# ──────────────────────────────────────────────────────────────────────────────
# Bot Events
# ──────────────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    """
    Event handler that runs when the bot successfully connects to Discord.
    It logs bot information, attempts OAuth login, and loads persistent data.
    """
    log.info(f"Bot is online as {bot.user.name} (ID {bot.user.id})")
    
    # Existing OAuth login flow check. This happens before USER_LINKS is populated below.
    if not USER_LINKS: # USER_LINKS is still empty here as it's not yet loaded from file
        log.warning("⚠️ No users linked (USER_LINKS is empty). Skipping OAuth login. Please run /linkid for at least one user and restart the bot.")
    else:
        # This branch might be executed if USER_LINKS has *already* been manually populated
        # or if previous logic populated it. With current changes, it will be empty here.
        log.info("🔐 Starting OAuth login flow in a visible Chrome window…")
        try:
            # Assumes BROWSER object handles login. If login fails, BROWSER might not be ready.
            if await BROWSER.login_oauth():
                log.info("✅ OAuth login successful. Bot ready to scrape.")
            else:
                log.error("❌ OAuth login automation failed. The bot will not be able to scrape without a valid eagle.ac cookie.")
        except Exception as e:
            log.error(f"❌ An error occurred during OAuth login automation: {e}")
            log.error("The bot will not be able to scrape without a valid eagle.ac cookie.")

    # Load linked players from persistent storage AFTER OAuth login (or attempt thereof)
    log.info("DISCORD_BOT: Attempting to load USER_LINKS from checkin_store in on_ready.")
    loaded_users = load_linked_players()
    if loaded_users:
        USER_LINKS.update(loaded_users)
        log.info(f"DISCORD_BOT: USER_LINKS updated with {len(USER_LINKS)} entries in on_ready.")
    else:
        log.info("DISCORD_BOT: No linked players loaded or file not found in on_ready. USER_LINKS remains empty.")


@bot.event
async def on_command_error(ctx, error):
    """
    Event handler for command errors.
    """
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Sorry, I don't know that command.")
    else:
        log.error(f"Error in command {ctx.command}: {error}")
        await ctx.send("An error occurred while processing your command.")

# ──────────────────────────────────────────────────────────────────────────────
# Bot Commands (Example - more commands would be added here)
# ──────────────────────────────────────────────────────────────────────────────
@bot.command(name="linkid")
async def link_user_id(ctx, sdvx_id: str):
    """
    Links a Discord user to an SDVX ID.
    Example: !linkid 123456789
    """
    try:
        user_id = ctx.author.id
        USER_LINKS[user_id] = sdvx_id
        save_linked_players(USER_LINKS) # Save updated USER_LINKS to file
        await ctx.send(f"Successfully linked Discord user {ctx.author.display_name} to SDVX ID: {sdvx_id}")
        log.info(f"Linked {ctx.author.display_name} (Discord ID: {user_id}) to SDVX ID: {sdvx_id}")
    except Exception as e:
        log.error(f"Error linking user ID: {e}")
        await ctx.send("An error occurred while linking your ID.")

@bot.command(name="showlinks")
async def show_links(ctx):
    """
    Shows all currently linked Discord users and their SDVX IDs.
    """
    if not USER_LINKS:
        await ctx.send("No users are currently linked.")
        return

    response = "Currently Linked Users:\n"
    for discord_id, sdvx_id in USER_LINKS.items():
        try:
            user = await bot.fetch_user(discord_id)
            response += f"- {user.display_name} (Discord ID: {discord_id}) -> SDVX ID: {sdvx_id}\n"
        except discord.NotFound:
            response += f"- Unknown User (ID: {discord_id}) -> SDVX ID: {sdvx_id} (User not found on Discord)\n"
    await ctx.send(response)
    log.info("Displayed linked users.")

@bot.command(name="unlinkid")
async def unlink_user_id(ctx):
    """
    Unlinks a Discord user from their SDVX ID.
    """
    user_id = ctx.author.id
    if user_id in USER_LINKS:
        del USER_LINKS[user_id]
        save_linked_players(USER_LINKS) # Save updated USER_LINKS to file
        await ctx.send(f"Successfully unlinked Discord user {ctx.author.display_name}.")
        log.info(f"Unlinked {ctx.author.display_name} (Discord ID: {user_id}).")
    else:
        await ctx.send("You are not currently linked.")

@bot.command(name="testscrape")
async def test_scrape_command(ctx, sdvx_id: str):
    """
    (Temporary/Development) Tests scraping a profile page directly.
    """
    await ctx.send(f"Attempting to scrape profile for SDVX ID: {sdvx_id}...")
    try:
        profile_data = await scrape_profile_page(sdvx_id)
        if profile_data:
            await ctx.send(f"Successfully scraped: {profile_data.get('player_name')} (VF: {profile_data.get('vf')})")
        else:
            await ctx.send("Failed to scrape profile. Check logs for errors.")
    except Exception as e:
        log.error(f"Error during test scrape: {e}")
        await ctx.send(f"An error occurred during scrape: {e}")
