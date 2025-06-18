import discord
from discord.ext import commands
from bot.core.identity_service import IdentityService
from bot.utils.embed_factory import create_embed

class IdentityCog(commands.Cog):
    def __init__(self, bot: commands.Bot, identity_service: IdentityService):
        self.bot = bot
        self.identity_service = identity_service

    @discord.app_commands.command(name="linkid", description="Link your SDVX ID to your Discord account.")
    @discord.app_commands.describe(sdvx_id="Your 8-digit SDVX ID (e.g., 1234-5678).")
    async def linkid(self, interaction: discord.Interaction, sdvx_id: str):
        success = await self.identity_service.link_user(str(interaction.user.id), sdvx_id)

        if success:
            embed = create_embed(
                title="Link Successful",
                description=f"Your account has been successfully linked to SDVX ID: `{sdvx_id}`.",
                theme="success"
            )
        else:
            embed = create_embed(
                title="Link Failed",
                description=f"The provided SDVX ID (`{sdvx_id}`) is invalid. Please use the format `1234-5678` or `12345678`.",
                theme="error"
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    identity_service = getattr(bot, "identity_service", None)
    if identity_service is None:
        raise RuntimeError("IdentityService is not attached to the bot.")
    await bot.add_cog(IdentityCog(bot, identity_service))