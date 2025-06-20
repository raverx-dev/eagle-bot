# bot/utils/notification_service.py

import discord
import os
from bot.config import log
from bot.utils.embed_factory import create_embed

class NotificationService:
    def __init__(self, bot: discord.Client):
        self.bot = bot

        # Admin alerts
        admin_channel_id_str = os.getenv("ADMIN_ALERT_CHANNEL_ID")
        self.admin_channel_id = None
        if admin_channel_id_str:
            try:
                self.admin_channel_id = int(admin_channel_id_str)
            except ValueError:
                log.error("ADMIN_ALERT_CHANNEL_ID in .env is not a valid integer.")

        # Session summaries
        session_log_channel_id_str = os.getenv("SESSION_LOG_CHANNEL_ID")
        self.session_log_channel_id = None
        if session_log_channel_id_str:
            try:
                self.session_log_channel_id = int(session_log_channel_id_str)
            except ValueError:
                log.error("SESSION_LOG_CHANNEL_ID in .env is not a valid integer.")
        else:
            log.warning("SESSION_LOG_CHANNEL_ID not set; automatic session summaries will be disabled.")

        # VF milestone announcements
        milestone_channel_id_str = os.getenv("MILESTONE_CHANNEL_ID")
        self.milestone_channel_id = None
        if milestone_channel_id_str:
            try:
                self.milestone_channel_id = int(milestone_channel_id_str)
            except ValueError:
                log.error("MILESTONE_CHANNEL_ID in .env is not a valid integer.")
        else:
            log.warning("MILESTONE_CHANNEL_ID not set; milestone announcements will be disabled.")

    async def send_admin_alert(self, message: str):
        if not self.admin_channel_id:
            return
        try:
            channel = self.bot.get_channel(self.admin_channel_id) or await self.bot.fetch_channel(self.admin_channel_id)
            if channel:
                await channel.send(message)
            else:
                log.error(f"Could not find admin alert channel with ID {self.admin_channel_id}.")
        except Exception as e:
            log.error(f"Failed to send admin alert to channel {self.admin_channel_id}: {e}", exc_info=True)

    async def send_session_reminder_dm(self, discord_id: int) -> bool:
        try:
            user = await self.bot.fetch_user(discord_id)
            embed = create_embed(
                title="Your Session is Idle",
                description="Your session has been paused due to inactivity.",
                theme="info",
                fields=[
                    {
                        "name": "What Happens Next?",
                        "value": "If you remain inactive for 5 more minutes, your session will be automatically checked out.",
                        "inline": False
                    },
                    {
                        "name": "How to Resume?",
                        "value": "Start a new play. Your session will resume automatically.",
                        "inline": False
                    },
                    {
                        "name": "Taking a Longer Break?",
                        "value": "Use the `/break` command to pause your session indefinitely and free up the machine for others.",
                        "inline": False
                    },
                    {
                        "name": "Finished Playing?",
                        "value": "Use the `/checkout` command to end your session now.",
                        "inline": False
                    }
                ]
            )
            await user.send(embed=embed)
            return True
        except Exception as e:
            log.warning(f"Failed to send idle reminder DM to user {discord_id}: {e}")
            return False

    async def post_session_summary(self, summary_data: dict):
        if not self.session_log_channel_id:
            log.warning(f"Cannot post session summary for {summary_data.get('player_name')}, channel not configured.")
            return

        initial_vf = summary_data.get('initial_volforce')
        final_vf = summary_data.get('final_volforce')
        vf_gained = "N/A"
        if isinstance(initial_vf, (int, float)) and isinstance(final_vf, (int, float)):
            vf_gained = f"{final_vf - initial_vf:+.3f}"

        fields = [
            {"name": "Session Duration", "value": f"{summary_data.get('session_duration_minutes', 0):.1f} min", "inline": True},
            {"name": "Total Songs Played", "value": str(summary_data.get('total_songs_played', 0)), "inline": True},
            {"name": "New Records", "value": ", ".join(summary_data.get('new_records', [])) if summary_data.get('new_records') else "None", "inline": False},
            {"name": "VF Gained", "value": vf_gained, "inline": True},
            {"name": "Initial VF", "value": f"{summary_data.get('initial_volforce', 0):.3f}", "inline": True},
            {"name": "Final VF", "value": f"{summary_data.get('final_volforce', 0):.3f}", "inline": True},
        ]

        embed = create_embed(
            title="🏁 Checked Out",
            description=(
                f"Session summary for **{summary_data.get('player_name', 'Player')}**. "
                "This session was ended automatically due to inactivity."
            ),
            theme="summary",
            fields=fields
        )
        try:
            channel = self.bot.get_channel(self.session_log_channel_id) or await self.bot.fetch_channel(self.session_log_channel_id)
            if channel:
                await channel.send(embed=embed)
            else:
                log.error(f"Could not find session log channel with ID {self.session_log_channel_id}.")
        except Exception as e:
            log.error(f"Failed to post session summary to channel {self.session_log_channel_id}: {e}", exc_info=True)

    async def post_vf_milestone_announcement(self, player_name: str, milestone: str):
        if not self.milestone_channel_id:
            log.warning(f"Cannot post VF milestone for {player_name}, channel not configured.")
            return

        embed = create_embed(
            title="🎉 New VolForce Milestone! 🎉",
            description=f"A huge congratulations to **{player_name}** for achieving a new rank!",
            theme="success",
            fields=[{"name": "New Milestone", "value": f"**{milestone}**", "inline": False}]
        )
        try:
            channel = (
                self.bot.get_channel(self.milestone_channel_id)
                or await self.bot.fetch_channel(self.milestone_channel_id)
            )
            if channel:
                await channel.send(embed=embed)
        except Exception as e:
            log.error(
                f"Failed to post VF milestone to channel {self.milestone_channel_id}: {e}",
                exc_info=True
            )
