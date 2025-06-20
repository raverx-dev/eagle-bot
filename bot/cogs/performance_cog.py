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
            embed = create_embed(
                title="Not Linked",
                description=f"{target_user.display_name} has not linked their SDVX ID.",
                theme="error"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # --- Rebuild the embed to match the new style ---
        player_name = user_profile.get('player_name', 'N/A')
        sdvx_id = user_profile.get('sdvx_id', 'N/A')
        title = f"📊 Stats for {player_name} ({sdvx_id})"

        fields = [
            {"name": "Volforce", "value": f"{user_profile.get('volforce', 0):.3f}", "inline": True},
            {"name": "Skill Level", "value": str(user_profile.get('skill_level', 'N/A')), "inline": True},
            {"name": "Total Plays", "value": str(user_profile.get('total_plays', 'N/A')), "inline": True}
        ]

        recent_plays = user_profile.get("recent_plays", [])
        if recent_plays:
            score_log = []
            for play in recent_plays[:5]:  # Take the top 5
                p_title = play.get('song_title', 'Unknown Song')
                p_chart = play.get('chart', '')
                p_grade = play.get('grade', '?')
                p_score = play.get('score', 'N/A')
                p_time = play.get('timestamp', '')
                score_log.append(f"• {p_title} {p_chart} {p_grade} {p_score} ({p_time})")
            log_value = "\n".join(score_log)
            fields.append({"name": "Last 5 Plays (Score Log)", "value": log_value, "inline": False})
        else:
            fields.append({"name": "Last 5 Plays (Score Log)", "value": "No recent plays found in cache.", "inline": False})

        embed = create_embed(title=title, theme="default", fields=fields)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="leaderboard", description="Shows the top 10 players on the arcade leaderboard.")
    async def leaderboard(self, interaction: discord.Interaction):
        leaderboard = self.performance_service.get_arcade_leaderboard_from_cache()
        if not leaderboard:
            embed = create_embed(
                title="🏆 Arcade 94 - SDVX Top 10",
                description="The leaderboard is currently empty.",
                theme="leaderboard"
            )
        else:
            desc_lines = [
                f"**#{p['rank']}** - {p.get('player_name', 'N/A')} - **{p.get('volforce', 0):.3f} VF**"
                for p in leaderboard
            ]
            embed = create_embed(
                title="🏆 Arcade 94 - SDVX Top 10",
                description="\n".join(desc_lines),
                theme="leaderboard"
            )
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    performance_service = getattr(bot, "performance_service", None)
    identity_service = getattr(bot, "identity_service", None)
    if not performance_service or not identity_service:
        raise RuntimeError("Required services not attached.")
    await bot.add_cog(PerformanceCog(bot, performance_service, identity_service))
