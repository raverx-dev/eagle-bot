import discord
import os

class NotificationService:
    def __init__(self, bot: discord.Client):
        self.bot = bot
        channel_id = os.getenv("ADMIN_ALERT_CHANNEL_ID")
        if not channel_id:
            raise Exception("ADMIN_ALERT_CHANNEL_ID environment variable is not set.")
        try:
            self.channel_id = int(channel_id)
        except ValueError:
            raise Exception("ADMIN_ALERT_CHANNEL_ID must be an integer.")

    async def send_admin_alert(self, message: str):
        if not self.channel_id:
            print("Admin channel ID is not set.")
            return
        channel = self.bot.get_channel(self.channel_id)
        if channel:
            await channel.send(message)
        else:
            print(f"Admin alert channel with ID {self.channel_id} not found.")