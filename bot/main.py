import asyncio
import os
import sys

# Add the parent directory to the Python path to allow imports from 'bot' package
# This is crucial for running the bot correctly from the project root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from bot.config import DISCORD_BOT_TOKEN, log
from bot.discord_bot import bot
from bot.checkin_store import USER_LINKS, load_linked_players

# ──────────────────────────────────────────────────────────────────────────────
# Main Bot Execution
# This section initializes and runs the Discord bot, handling its lifecycle
# and integrating persistent data loading.
# ──────────────────────────────────────────────────────────────────────────────
async def main():
    """
    The main asynchronous function to start and run the Discord bot.
    It loads persistent user data before starting the bot's connection to Discord.
    """
    log.info("MAIN: Starting bot execution flow.")

    # Load linked players from persistent storage on startup
    log.info("MAIN: Calling load_linked_players from checkin_store.")
    loaded_users = load_linked_players()
    USER_LINKS.update(loaded_users)
    log.info(f"MAIN: USER_LINKS dictionary updated with {len(USER_LINKS)} entries.")

    log.info("MAIN: Attempting to start Discord bot connection.")
    try:
        await bot.start(DISCORD_BOT_TOKEN)
    except Exception as e:
        log.error(f"MAIN: Bot failed to start: {e}")
    finally:
        await bot.close()
        log.info("MAIN: Bot stopped.")

if __name__ == "__main__":
    log.info("MAIN: Script execution started from __main__ block.")
    # Ensure a .env file exists for environment variables
    if not os.path.exists('.env'):
        log.error("MAIN: '.env' file not found. Please create one with DISCORD_BOT_TOKEN.")
        sys.exit(1)

    # Check for Discord Bot Token
    if not DISCORD_BOT_TOKEN:
        log.error("MAIN: DISCORD_BOT_TOKEN is not set in the .env file. Please add it.")
        sys.exit(1)

    asyncio.run(main())
    log.info("MAIN: Async event loop finished.")
