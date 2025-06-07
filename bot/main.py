# ──────────────────────────────────────────────────────────────────────────────
# FILE: bot/main.py
# ──────────────────────────────────────────────────────────────────────────────

# Import configuration from the new config module
from bot.config import DISCORD_BOT_TOKEN, log

# Import the bot object from the new discord_bot module
from bot.discord_bot import bot

# ──────────────────────────────────────────────────────────────────────────────
# Run the bot
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
