import discord
from typing import Optional
from discord.ext import commands
from bot.core.session_service import SessionService
from bot.core.identity_service import IdentityService
from bot.utils.error_handler import ScrapeErrorHandler
from bot.utils.embed_factory import create_embed

@discord.app_commands.default_permissions(administrator=True)
class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot, session_service: SessionService, identity_service: IdentityService, error_handler: ScrapeErrorHandler):
        self.bot = bot
        self.session_service = session_service
        self.identity_service = identity_service
        self.error_handler = error_handler

    @discord.app_commands.command(name="botstatus", description="Checks the operational status of the bot.")
    async def botstatus(self, interaction: discord.Interaction):
        system_status = "DOWN" if self.error_handler.system_is_down else "UP"
        session_count = self.session_service.get_session_count()
        desc = f"**System Status:** {system_status}\n**Active Sessions:** {session_count}"
        embed = create_embed(
            title="Bot Status",
            description=desc,
            theme="default"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="force_checkout", description="Forcibly ends a user's session.")
    async def force_checkout(self, interaction: discord.Interaction, user: discord.User):
        result = self.session_service.force_checkout(user.id)
        if result:
            embed = create_embed(
                title="Force Checkout",
                description=f"Successfully checked out {user.display_name}.",
                theme="success"
            )
        else:
            embed = create_embed(
                title="Force Checkout Failed",
                description=f"No active session found for {user.display_name}.",
                theme="error"
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="force_unlink", description="Forcibly unlinks a user's SDVX ID.")
    async def force_unlink(self, interaction: discord.Interaction, user: discord.User):
        result = self.identity_service.force_unlink(str(user.id))
        if result:
            embed = create_embed(
                title="Force Unlink",
                description=f"Successfully unlinked {user.display_name}.",
                theme="success"
            )
        else:
            embed = create_embed(
                title="Force Unlink Failed",
                description=f"No link found for {user.display_name}.",
                theme="error"
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    session_service = getattr(bot, "session_service", None)
    identity_service = getattr(bot, "identity_service", None)
    error_handler = getattr(bot, "error_handler", None)
    if not session_service or not identity_service or not error_handler:
        raise RuntimeError("SessionService, IdentityService, and ScrapeErrorHandler must be attached to the bot.")
    await bot.add_cog(AdminCog(bot, session_service, identity_service, error_handler))
