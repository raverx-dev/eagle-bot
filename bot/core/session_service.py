# bot/core/session_service.py
import json
import copy
import asyncio
import os
from datetime import datetime, timezone, timedelta
from bot.core.performance_service import PerformanceService
from bot.config import log
from bot.eagle_browser import EagleBrowser
from bot.core.role_service import RoleService

class SessionService:
    def __init__(self, sessions_file_path: str, performance_service: PerformanceService, browser: EagleBrowser, role_service=None):
        self.sessions_file_path = sessions_file_path
        self.performance_service = performance_service
        self.browser = browser
        self.role_service = role_service
        self.IDLE_TIMEOUT_MIN = 10
        self.BREAK_TIMEOUT_MIN = 5
        self.sessions = self._blocking_read_sessions()
        log.info(f"SESSION_SVC: Loaded {len(self.sessions)} sessions into memory.")

    def _get_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _blocking_read_sessions(self) -> dict:
        try:
            with open(self.sessions_file_path, "r", encoding="utf-8") as f: return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): return {}
        except Exception as e:
            log.error(f"!!! FAILED TO READ from {self.sessions_file_path}: {e}", exc_info=True)
            return {}

    def _blocking_write_sessions(self):
        try:
            os.makedirs(os.path.dirname(self.sessions_file_path), exist_ok=True)
            with open(self.sessions_file_path, "w", encoding="utf-8") as f: json.dump(self.sessions, f, ensure_ascii=False, indent=4)
        except Exception as e: log.error(f"!!! FAILED TO WRITE SESSIONS: {e}", exc_info=True)

    async def _write_sessions(self):
        await asyncio.to_thread(self._blocking_write_sessions)

    async def get_active_session(self) -> dict | None:
        for session_data in self.sessions.values():
            if session_data.get("status") == "active": return session_data
        return None

    async def process_new_score(self, discord_id: str):
        active_session = await self.get_active_session()
        if active_session and active_session.get("discord_id") != discord_id: return
        now_iso = self._get_now().isoformat()
        session = self.sessions.get(discord_id)
        if not session:
            self.sessions[discord_id] = { "discord_id": discord_id, "status": "active", "type": "auto", "start_time": now_iso, "last_activity": now_iso }
            if self.role_service: await self.role_service.assign_role(discord_id)
        elif session.get("status") == "on_break":
            session["status"] = "active"
            session["last_activity"] = now_iso
            if self.role_service: await self.role_service.assign_role(discord_id)
        else:
            session["last_activity"] = now_iso
        await self._write_sessions()

    async def start_manual_session(self, discord_id: str) -> bool:
        if await self.get_active_session(): return False
        user_profile = await self.performance_service.identity_service.get_user_by_discord_id(discord_id)
        initial_volforce = user_profile.get("volforce") if user_profile else None
        now_iso = self._get_now().isoformat()
        self.sessions[discord_id] = {
            "discord_id": discord_id, "status": "active", "type": "manual",
            "start_time": now_iso, "last_activity": now_iso,
            "initial_volforce": initial_volforce
        }
        await self._write_sessions()
        if self.role_service: await self.role_service.assign_role(discord_id)
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
        user_profile = await self.performance_service.identity_service.get_user_by_discord_id(discord_id)
        if not user_profile: return {}

        old_volforce = session.get("initial_volforce")
        final_volforce = user_profile.get("volforce")
        recent_plays = user_profile.get("recent_plays", [])
        
        duration_minutes = 0
        # --- ROBUST TIMESTAMP HANDLING ---
        try:
            start_dt = datetime.fromisoformat(session.get("start_time")) if session.get("start_time") else None
            if start_dt:
                duration_minutes = ((self._get_now() - start_dt).total_seconds() / 60)
        except Exception as e:
            log.warning(f"Could not parse session start_time for duration calculation: {e}")
        # --- END ROBUST HANDLING ---

        new_records = self.performance_service.analyze_new_scores_for_records(recent_plays)
        vf_milestone = self.performance_service.check_for_vf_milestone(old_volforce, final_volforce)
        
        return {
            "player_name": user_profile.get("player_name"), "sdvx_id": user_profile.get("sdvx_id"),
            "session_duration_minutes": duration_minutes,
            "new_records": [play.get("song_title") for play in new_records if play.get("song_title")],
            "vf_milestone": vf_milestone,
            "initial_volforce": old_volforce, "final_volforce": final_volforce
        }

    async def pause_session(self, discord_id: str) -> bool:
        session = self.sessions.get(discord_id)
        if not session or session.get("status") != "active": return False
        session["status"] = "on_break"
        session["last_activity"] = self._get_now().isoformat()
        await self._write_sessions()
        if self.role_service: await self.role_service.remove_role(discord_id)
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
                changes_made = True
                if self.role_service: await self.role_service.remove_role(discord_id)
            elif session.get("status") == "pending_break" and minutes_idle > self.BREAK_TIMEOUT_MIN:
                sessions_to_delete.append(discord_id)
        if sessions_to_delete:
            for discord_id in sessions_to_delete:
                await self.end_session(discord_id)
        elif changes_made:
            await self._write_sessions()

    def get_session_count(self) -> int:
        return len(self.sessions)