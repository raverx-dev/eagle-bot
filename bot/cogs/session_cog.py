import discord
from discord.ext import commands

from bot.core.session_service import SessionService
from bot.core.identity_service import IdentityService
from bot.utils.embed_factory import create_embed
from bot.config import log

class SessionCog(commands.Cog):
    def __init__(self, bot: commands.Bot, session_service: SessionService, identity_service: IdentityService):
        self.bot = bot
        self.session_service = session_service
        self.identity_service = identity_service

    @discord.app_commands.command(name="checkin", description="Manually start your play session.")
    async def checkin(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        log.info(f"CHECKIN_COG: Received command from {user_id}")
        user_profile = await self.identity_service.get_user_by_discord_id(user_id)
        
        if not user_profile or not user_profile.get("sdvx_id"):
            embed = create_embed(
                title="Check-in Failed",
                description="You must link your SDVX ID first using the `/linkid` command.",
                theme="error"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        result = await self.session_service.start_manual_session(user_id)
        if result:
            sdvx_id = user_profile.get("sdvx_id", "N/A")
            skill = user_profile.get("skill_level", "N/A")
            plays = user_profile.get("total_plays", "N/A")
            description = (
                f"**SDVX ID:** `{sdvx_id}` • "
                f"**VF:** `{user_profile.get('volforce', 0):.3f}` • "
                f"**Skill:** `{skill}` • "
                f"**Plays:** `{plays}`"
            )
            embed = create_embed(title="✅ Checked In", description=description, theme="success")
        else:
            embed = create_embed(
                title="Check-in Failed",
                description="Another player's session is already active.",
                theme="error"
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="checkout", description="End your play session.")
    async def checkout(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        log.info(f"CHECKOUT_COG: Received command from {user_id}")
        
        session_summary = await self.session_service.end_session(user_id)
        if not session_summary:
            embed = create_embed(
                title="Checkout Failed",
                description="No active session found to check out.",
                theme="error"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        initial_vf = session_summary.get('initial_volforce')
        final_vf = session_summary.get('final_volforce')
        vf_gained = "N/A"
        if isinstance(initial_vf, (int, float)) and isinstance(final_vf, (int, float)):
            vf_gained = f"{final_vf - initial_vf:+.3f}"

        fields = [
            {"name": "Session Duration", "value": f"{session_summary.get('session_duration_minutes', 0):.1f} min", "inline": True},
            {"name": "Total Songs Played", "value": str(session_summary.get('total_songs_played', 0)), "inline": True},
            # Add this line:
            {"name": "New Records", "value": ", ".join(session_summary.get('new_records', [])) if session_summary.get('new_records') else "None", "inline": False},
            {"name": "VF Gained", "value": vf_gained, "inline": True},
            {"name": "VF at Check-in", "value": f"{initial_vf:.3f}" if initial_vf else "N/A", "inline": True},
            {"name": "VF Now", "value": f"{final_vf:.3f}" if final_vf else "N/A", "inline": True},
        ]
        
        embed = create_embed(
            title="🏁 Checked Out",
            description=f"Session summary for **{session_summary.get('player_name', 'Player')}**.",
            theme="summary",
            fields=fields
        )
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="break", description="Pause your current session.")
    async def break_session(self, interaction: discord.Interaction):
        result = await self.session_service.pause_session(str(interaction.user.id))
        if result:
            embed = create_embed(
                title="⏸️ Session Paused",
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
    identity_service = getattr(bot, "identity_service", None)
    if not session_service or not identity_service:
        raise RuntimeError("SessionService or IdentityService not attached to bot.")
    await bot.add_cog(SessionCog(bot, session_service, identity_service))
