import discord
from typing import Optional
from discord.ext import commands
from bot.config import log
from bot.core.performance_service import PerformanceService
from bot.core.identity_service import IdentityService
from bot.utils.embed_factory import create_embed

class PerformanceCog(commands.Cog):
    def __init__(self, bot: commands.Bot, performance_service: PerformanceService, identity_service: IdentityService):
        self.bot = bot
        self.performance_service = performance_service
        self.identity_service = identity_service

    @discord.app_commands.command(name="stats", description="View your or another player's stats.")
    @discord.app_commands.describe(user="The user whose stats you want to see (defaults to you).")
    async def stats(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        target_user = user or interaction.user
        user_profile = await self.identity_service.get_user_by_discord_id(str(target_user.id))
        if not user_profile or not user_profile.get("sdvx_id"):
            embed = create_embed(title="Not Linked", description=f"{target_user.display_name} has not linked their SDVX ID.", theme="error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        sdvx_id = user_profile["sdvx_id"]
        stats = self.performance_service.get_player_stats_from_cache(sdvx_id)
        if not stats:
            embed = create_embed(title="No Stats Found", description="No stats found for this player in the cache.", theme="error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        desc = (f"**Player:** {stats.get('player_name', 'N/A')}\n"
                f"**Volforce:** {stats.get('volforce', 'N/A')}\n"
                f"**Rank:** {stats.get('rank', 'N/A')}")
        embed = create_embed(title=f"Stats for {stats.get('player_name', target_user.display_name)}", description=desc, theme="default")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="leaderboard", description="Shows the top 10 players on the arcade leaderboard.")
    async def leaderboard(self, interaction: discord.Interaction):
        leaderboard = self.performance_service.get_arcade_leaderboard_from_cache()
        if not leaderboard:
            embed = create_embed(title="Leaderboard", description="The leaderboard is currently empty.", theme="default")
        else:
            desc_lines = [f"**#{p['rank']}** - {p.get('player_name', 'N/A')} - **{p.get('volforce', 'N/A')} VF**" for p in leaderboard]
            embed = create_embed(title="Arcade Leaderboard", description="\n".join(desc_lines), theme="default")
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    performance_service = getattr(bot, "performance_service", None)
    identity_service = getattr(bot, "identity_service", None)
    if not performance_service or not identity_service: raise RuntimeError("Required services not attached.")
    await bot.add_cog(PerformanceCog(bot, performance_service, identity_service))