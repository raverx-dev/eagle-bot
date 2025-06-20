# bot/main.py
import os
import asyncio
import discord
from discord.ext import commands

from bot.config import log, DISCORD_BOT_TOKEN
from bot.eagle_browser import EagleBrowser
from bot.core.identity_service import IdentityService
from bot.core.session_service import SessionService
from bot.core.performance_service import PerformanceService
from bot.core.system_service import SystemService
from bot.core.role_service import RoleService
from bot.utils.chronos import Chronos
from bot.utils.error_handler import ScrapeErrorHandler
from bot.utils.notification_service import NotificationService # Import the new service

async def main():
    if not DISCORD_BOT_TOKEN:
        log.error("❌ DISCORD_BOT_TOKEN not found in config.py or .env file.")
        return

    GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
    NOW_PLAYING_ROLE_NAME = "Now Playing"

    log.info("Initializing bot and services...")
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="!", intents=intents)

    browser = EagleBrowser()
    if not browser.init_headless_chrome():
        log.error("❌ Bot cannot start without a headless browser. Exiting.")
        return

    identity_service = IdentityService("data/users.json", browser)
    performance_service = PerformanceService("data/users.json")
    performance_service.identity_service = identity_service
    role_service = RoleService(bot, GUILD_ID, NOW_PLAYING_ROLE_NAME)
    
    # Create the real NotificationService instance
    notification_service = NotificationService(bot)

    # Inject NotificationService into SessionService
    session_service = SessionService(
        sessions_file_path="data/sessions.json",
        performance_service=performance_service,
        browser=browser,
        role_service=role_service,
        notification_service=notification_service
    )
    system_service = SystemService("data/arcade_schedule.json")
    
    # The error handler can now also use the real notification service
    error_handler = ScrapeErrorHandler(notification_service=notification_service)

    log.info("Attaching services to bot instance...")
    bot.identity_service = identity_service
    bot.performance_service = performance_service
    bot.session_service = session_service
    bot.error_handler = error_handler
    bot.role_service = role_service
    bot.notification_service = notification_service # Attach new service

    chronos = Chronos(system_service, identity_service, session_service, error_handler=error_handler)

    @bot.event
    async def on_ready():
        log.info(f'✅ Logged in as {bot.user}')
        
        try:
            await bot.wait_until_ready()
            guild = await bot.fetch_guild(GUILD_ID)
            if guild:
                role = discord.utils.get(guild.roles, name=NOW_PLAYING_ROLE_NAME)
                if role:
                    bot.role_service.guild = guild
                    bot.role_service.role = role
                    log.info("✅ RoleService fully initialized with guild and role.")
                else:
                    log.error(f"❌ Role '{NOW_PLAYING_ROLE_NAME}' not found. Role management disabled.")
                    bot.role_service = None
            else:
                log.error(f"❌ Guild with ID {GUILD_ID} not found. Role management disabled.")
                bot.role_service = None
        except Exception as e:
            log.error(f"❌ An unexpected error occurred during RoleService initialization: {e}", exc_info=True)
            bot.role_service = None

        log.info('Starting Chronos background task...')
        asyncio.create_task(chronos.start())
        
        my_guild = discord.Object(id=GUILD_ID)
        log.info(f"Syncing application commands to guild: {GUILD_ID}...")
        bot.tree.copy_global_to(guild=my_guild)
        await bot.tree.sync(guild=my_guild)
        log.info('✅ Commands synced.')

    log.info("Loading cogs...")
    initial_extensions = [
        "bot.cogs.identity_cog", "bot.cogs.session_cog",
        "bot.cogs.performance_cog", "bot.cogs.admin_cog"
    ]
    for extension in initial_extensions:
        await bot.load_extension(extension)
    log.info("✅ Cogs loaded.")

    try:
        log.info("🚀 Starting bot...")
        await bot.start(DISCORD_BOT_TOKEN)
    finally:
        log.info("🛑 Bot shutting down. Closing headless browser.")
        browser.quit_headless()

if __name__ == "__main__":
    asyncio.run(main())