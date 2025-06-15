import discord
from discord.ext import commands
from bot.core.session_service import SessionService
from bot.utils.embed_factory import create_embed

class SessionCog(commands.Cog):
    def __init__(self, bot: commands.Bot, session_service: SessionService):
        self.bot = bot
        self.session_service = session_service

    @discord.app_commands.command(name="checkin", description="Manually start your play session.")
    async def checkin(self, interaction: discord.Interaction):
        result = self.session_service.start_manual_session(interaction.user.id)
        if result:
            embed = create_embed(
                title="Session Started",
                description="You have successfully checked in.",
                theme="success"
            )
        else:
            embed = create_embed(
                title="Check-in Failed",
                description="Another player's session is already active.",
                theme="error"
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="checkout", description="End your play session.")
    async def checkout(self, interaction: discord.Interaction):
        self.session_service.end_session(interaction.user.id)
        embed = create_embed(
            title="Session Ended",
            description="You have been checked out.",
            theme="success"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="break", description="Pause your current session.")
    async def break_session(self, interaction: discord.Interaction):
        result = self.session_service.pause_session(interaction.user.id)
        if result:
            embed = create_embed(
                title="Session Paused",
                description="Your session has been paused.",
                theme="success"
            )
        else:
            embed = create_embed(
                title="Pause Failed",
                description="Could not pause. No active session found.",
                theme="error"
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    session_service = getattr(bot, "session_service", None)
    if session_service is None:
        raise RuntimeError("SessionService is not attached to the bot.")
    await bot.add_cog(SessionCog(bot, session_service))
