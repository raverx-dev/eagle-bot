# bot/cogs/session_cog.py
import discord
from discord.ext import commands

# Make sure services and logger are importable
from bot.core.session_service import SessionService
from bot.core.identity_service import IdentityService
from bot.utils.embed_factory import create_embed
from bot.config import log # Import the logger

class SessionCog(commands.Cog):
    def __init__(self, bot: commands.Bot, session_service: SessionService, identity_service: IdentityService):
        self.bot = bot
        self.session_service = session_service
        self.identity_service = identity_service

    @discord.app_commands.command(name="checkin", description="Manually start your play session.")
    async def checkin(self, interaction: discord.Interaction):
        # This is the improved logic we discussed earlier.
        # It ensures a user is linked before they can check in.
        user_id = str(interaction.user.id)
        log.info(f"CHECKIN_COG: Received command from {user_id}")
        user_profile = await self.identity_service.get_user_by_discord_id(user_id)
        
        if not user_profile or not user_profile.get("sdvx_id"):
            embed = create_embed(title="Check-in Failed", description="You must link your SDVX ID first using the `/linkid` command.", theme="error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        result = await self.session_service.start_manual_session(user_id)
        if result:
            embed = create_embed(title="Session Started", description="You have successfully checked in.", theme="success")
        else:
            embed = create_embed(title="Check-in Failed", description="Another player's session is already active.", theme="error")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="checkout", description="End your play session.")
    async def checkout(self, interaction: discord.Interaction):
        # --- DIAGNOSTIC LOGGING ---
        user_id = str(interaction.user.id)
        log.info(f"CHECKOUT_COG: Received command from {user_id}")
        log.info("CHECKOUT_COG: Calling self.session_service.end_session...")
        
        session_summary = await self.session_service.end_session(user_id)
        
        log.info("CHECKOUT_COG: self.session_service.end_session call completed.")
        # --- END DIAGNOSTIC LOGGING ---

        if not session_summary:
            embed = create_embed(title="Checkout Failed", description="No active session found to check out.", theme="error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Build fields for the summary
        fields = [
            {"name": "Duration", "value": f"{session_summary.get('session_duration_minutes', 0):.1f} minutes", "inline": True},
            {"name": "Initial VF", "value": str(session_summary.get('initial_volforce', 'N/A')), "inline": True},
            {"name": "Final VF", "value": str(session_summary.get('final_volforce', 'N/A')), "inline": True},
            {"name": "New Records", "value": ", ".join(session_summary.get('new_records', [])) if session_summary.get('new_records') else "None", "inline": False},
            {"name": "VF Milestone", "value": session_summary.get('vf_milestone', 'None') or "None", "inline": True}
        ]
        embed = create_embed(
            title=f"Session Summary for {session_summary.get('player_name', 'Player')}",
            description="Your session has ended.",
            theme="success",
            fields=fields
        )
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="break", description="Pause your current session.")
    async def break_session(self, interaction: discord.Interaction):
        result = await self.session_service.pause_session(str(interaction.user.id))
        if result:
            embed = create_embed(title="Session Paused", description="Your session has been paused.", theme="success")
        else:
            embed = create_embed(title="Pause Failed", description="Could not pause. No active session found.", theme="error")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    # This cog now depends on both services
    session_service = getattr(bot, "session_service", None)
    identity_service = getattr(bot, "identity_service", None)
    if not session_service or not identity_service:
        raise RuntimeError("SessionService or IdentityService not attached to bot.")
    await bot.add_cog(SessionCog(bot, session_service, identity_service))