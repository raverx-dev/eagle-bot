# bot/core/session_service.py
import json
import asyncio
import os
from datetime import datetime, timezone, timedelta

from bot.core.performance_service import PerformanceService
from bot.config import log
from bot.eagle_browser import EagleBrowser
from bot.core.role_service import RoleService
from bot.utils.notification_service import NotificationService

class SessionService:
    def __init__(
        self,
        sessions_file_path: str,
        performance_service: PerformanceService,
        browser: EagleBrowser,
        role_service: RoleService,
        notification_service: NotificationService
    ):
        self.sessions_file_path = sessions_file_path
        self.performance_service = performance_service
        self.browser = browser
        self.role_service = role_service
        self.notification_service = notification_service
        self.IDLE_TIMEOUT_MIN = 5
        self.BREAK_TIMEOUT_MIN = 5
        self.ON_BREAK_TIMEOUT_HOURS = 8
        self.sessions = self._blocking_read_sessions()
        log.info(f"SESSION_SVC: Loaded {len(self.sessions)} sessions into memory.")

    def _get_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _blocking_read_sessions(self) -> dict:
        try:
            with open(self.sessions_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        except Exception as e:
            log.error(f"!!! FAILED TO READ from {self.sessions_file_path}: {e}", exc_info=True)
            return {}

    async def _write_sessions(self):
        await asyncio.to_thread(self._blocking_write_sessions)

    def _blocking_write_sessions(self):
        try:
            os.makedirs(os.path.dirname(self.sessions_file_path), exist_ok=True)
            with open(self.sessions_file_path, "w", encoding="utf-8") as f:
                json.dump(self.sessions, f, ensure_ascii=False, indent=4)
        except Exception as e:
            log.error(f"!!! FAILED TO WRITE SESSIONS: {e}", exc_info=True)

    async def get_active_session(self) -> dict | None:
        for session_data in self.sessions.values():
            if session_data.get("status") == "active":
                return session_data
        return None

    async def process_new_score(self, discord_id: str):
        active_session = await self.get_active_session()
        if active_session and active_session.get("discord_id") != discord_id:
            return
        now_iso = self._get_now().isoformat()
        session = self.sessions.get(discord_id)

        if not session:
            user_profile = await self.performance_service.identity_service.get_user_by_discord_id(discord_id)
            initial_volforce = user_profile.get("volforce") if user_profile else None
            self.sessions[discord_id] = {
                "discord_id": discord_id,
                "status": "active",
                "type": "auto",
                "start_time": now_iso,
                "last_activity": now_iso,
                "reminder_sent": False,
                "initial_volforce": initial_volforce,
                "songs_played_count": 1  # NEW: An auto-session starts on the first song.
            }
            if self.role_service:
                await self.role_service.assign_role(discord_id)

        elif session.get("status") in ("on_break", "pending_break"):
            session["status"] = "active"
            session["last_activity"] = now_iso
            session["songs_played_count"] = session.get("songs_played_count", 0) + 1
            if self.role_service:
                await self.role_service.assign_role(discord_id)
        else:
            session["last_activity"] = now_iso
            session["songs_played_count"] = session.get("songs_played_count", 0) + 1

        await self._write_sessions()

    async def start_manual_session(self, discord_id: str) -> bool:
        if await self.get_active_session():
            return False
        user_profile = await self.performance_service.identity_service.get_user_by_discord_id(discord_id)
        initial_volforce = user_profile.get("volforce") if user_profile else None
        now_iso = self._get_now().isoformat()
        self.sessions[discord_id] = {
            "discord_id": discord_id,
            "status": "active",
            "type": "manual",
            "start_time": now_iso,
            "last_activity": now_iso,
            "initial_volforce": initial_volforce,
            "reminder_sent": False,
            "songs_played_count": 0  # NEW: A manual session starts with 0 songs played.
        }
        await self._write_sessions()
        if self.role_service:
            await self.role_service.assign_role(discord_id)
        return True

    async def end_session(self, discord_id: str) -> dict | None:
        if discord_id in self.sessions:
            session_summary = await self._analyze_session_data(discord_id)
            del self.sessions[discord_id]
            await self._write_sessions()
            if self.role_service:
                await self.role_service.remove_role(discord_id)
            return session_summary
        return None

    async def _analyze_session_data(self, discord_id: str) -> dict:
        session = self.sessions.get(discord_id, {})

        # --- Safely parse session start time ---
        session_start_dt = None
        try:
            # The session start_time is already in ISO format with timezone
            if session.get("start_time"):
                session_start_dt = datetime.fromisoformat(session.get("start_time"))
        except (TypeError, ValueError) as e:
            log.warning(f"Could not parse session start_time for record filtering: {e}")

        user_profile = await self.performance_service.identity_service.get_user_by_discord_id(discord_id)
        if not user_profile:
            return {}

        old_volforce = session.get("initial_volforce")
        final_volforce = user_profile.get("volforce")
        recent_plays = user_profile.get("recent_plays", [])
        total_songs_played = session.get("songs_played_count", 0)  # NEW: Get song count
        duration_minutes = 0
        try:
            start_dt = datetime.fromisoformat(session.get("start_time"))
            duration_minutes = ((self._get_now() - start_dt).total_seconds() / 60)
        except (TypeError, ValueError):
            pass

        # --- Filter recent plays to only include those from the current session ---
        session_plays = []
        if session_start_dt:
            for play in recent_plays:
                try:
                    # The timestamp from the scrape is like "2025-06-18 10:56 PM"
                    play_dt = datetime.strptime(play["timestamp"], "%Y-%m-%d %I:%M %p").replace(tzinfo=timezone.utc)
                    if play_dt >= session_start_dt:
                        session_plays.append(play)
                except (ValueError, TypeError, KeyError):
                    continue  # Skip plays with malformed timestamps

        # Now, find new records ONLY from the plays that happened during this session
        new_records_full = self.performance_service.analyze_new_scores_for_records(session_plays)
        vf_milestone = self.performance_service.check_for_vf_milestone(old_volforce, final_volforce)

        if vf_milestone:
            player_name = user_profile.get("player_name", "A Player")
            await self.notification_service.post_vf_milestone_announcement(player_name, vf_milestone)

        return {
            "player_name": user_profile.get("player_name"),
            "sdvx_id": user_profile.get("sdvx_id"),
            "session_duration_minutes": duration_minutes,
            "total_songs_played": total_songs_played,  # NEW: Add to summary data
            "new_records": new_records_full,
            "vf_milestone": vf_milestone,
            "initial_volforce": old_volforce,
            "final_volforce": final_volforce
        }

    async def pause_session(self, discord_id: str) -> bool:
        session = self.sessions.get(discord_id)
        if not session or session.get("status") != "active":
            return False
        session["status"] = "on_break"
        session["last_activity"] = self._get_now().isoformat()
        await self._write_sessions()
        if self.role_service:
            await self.role_service.remove_role(discord_id)
        return True

    async def force_checkout(self, discord_id: str) -> bool:
        if discord_id in self.sessions:
            await self.end_session(discord_id)
            return True
        return False

    async def find_and_end_stale_sessions(self):
        now = self._get_now()
        sessions_to_delete = []
        changes_made = False
        for discord_id, session in list(self.sessions.items()):
            last_activity_dt = datetime.fromisoformat(session.get("last_activity"))
            minutes_idle = (now - last_activity_dt).total_seconds() / 60

            if session.get("status") == "active" and minutes_idle > self.IDLE_TIMEOUT_MIN:
                session["status"] = "pending_break"
                session["last_activity"] = now.isoformat()
                if not session.get("reminder_sent"):
                    await self.notification_service.send_session_reminder_dm(int(discord_id))
                    session["reminder_sent"] = True
                changes_made = True
                if self.role_service:
                    await self.role_service.remove_role(discord_id)

            elif session.get("status") == "pending_break" and minutes_idle > self.BREAK_TIMEOUT_MIN:
                sessions_to_delete.append(discord_id)

            elif session.get("status") == "on_break" and minutes_idle > (self.ON_BREAK_TIMEOUT_HOURS * 60):
                log.info(f"SESSION_SVC: Cleaning up 'on_break' session for {discord_id}.")
                sessions_to_delete.append(discord_id)

        if sessions_to_delete:
            for discord_id in sessions_to_delete:
                summary = await self.end_session(discord_id)
                if summary:
                    await self.notification_service.post_session_summary(summary)

        elif changes_made:
            await self._write_sessions()

    def get_session_count(self) -> int:
        return len(self.sessions)
