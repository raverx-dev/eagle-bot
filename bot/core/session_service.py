import json
import copy
from datetime import datetime, timezone, timedelta

# We expect PerformanceService to be defined, even if it's a placeholder
from bot.core.performance_service import PerformanceService

class SessionService:
    def __init__(self, sessions_file_path: str, performance_service: PerformanceService):
        self.sessions_file_path = sessions_file_path
        self.performance_service = performance_service
        self.IDLE_TIMEOUT_MIN = 10
        self.BREAK_TIMEOUT_MIN = 5

    def _get_now(self) -> datetime:
        """Helper to get the current time, making it mockable for tests."""
        return datetime.now(timezone.utc)

    def _read_sessions(self) -> dict:
        try:
            with open(self.sessions_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._write_sessions({})
            return {}

    def _write_sessions(self, data: dict):
        with open(self.sessions_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def _get_active_session(self) -> dict | None:
        sessions = self._read_sessions()
        for session_data in sessions.values():
            if session_data.get("status") == "active":
                return session_data
        return None

    def process_new_score(self, discord_id: str):
        active_session = self._get_active_session()
        if active_session and active_session.get("discord_id") != discord_id:
            return

        sessions = self._read_sessions()
        now_iso = self._get_now().isoformat()
        session = sessions.get(discord_id)

        if not session:
            sessions[discord_id] = {
                "discord_id": discord_id,
                "status": "active",
                "type": "auto",
                "start_time": now_iso,
                "last_activity": now_iso
            }
        else:
            session["status"] = "active"
            session["last_activity"] = now_iso
        
        self._write_sessions(sessions)

    def start_manual_session(self, discord_id: str) -> bool:
        """Starts a manual session if no other session is active."""
        if self._get_active_session():
            return False

        sessions = self._read_sessions()
        now_iso = self._get_now().isoformat()
        
        sessions[discord_id] = {
            "discord_id": discord_id,
            "status": "active",
            "type": "manual",
            "start_time": now_iso,
            "last_activity": now_iso
        }
        self._write_sessions(sessions)
        return True

    def pause_session(self, discord_id: str) -> bool:
        """Pauses a user's active session, setting it to 'on_break'."""
        sessions = self._read_sessions()
        session = sessions.get(discord_id)

        if not session or session.get("status") != "active":
            return False
        
        session["status"] = "on_break"
        session["last_activity"] = self._get_now().isoformat()
        self._write_sessions(sessions)
        return True

    def end_session(self, discord_id: str):
        sessions = self._read_sessions()
        if discord_id in sessions:
            del sessions[discord_id]
            self._write_sessions(sessions)

    def force_checkout(self, discord_id: str) -> bool:
        """Admin function to forcibly end a user's session."""
        sessions = self._read_sessions()
        if discord_id in sessions:
            self.end_session(discord_id)
            return True
        return False

    async def find_and_end_stale_sessions(self):
        sessions = self._read_sessions()
        original_sessions = copy.deepcopy(sessions)
        now = self._get_now()
        
        sessions_to_delete = []

        for discord_id, session in sessions.items():
            last_activity_str = session.get("last_activity")
            if not last_activity_str: continue
            
            try:
                last_activity_dt = datetime.fromisoformat(last_activity_str)
            except ValueError: continue

            minutes_idle = (now - last_activity_dt).total_seconds() / 60

            if session.get("status") == "active" and minutes_idle > self.IDLE_TIMEOUT_MIN:
                session["status"] = "pending_break"
                session["last_activity"] = now.isoformat()
            elif session.get("status") == "pending_break" and minutes_idle > self.BREAK_TIMEOUT_MIN:
                sessions_to_delete.append(discord_id)

        for discord_id in sessions_to_delete:
            if discord_id in sessions:
                del sessions[discord_id]
        
        if sessions != original_sessions:
            self._write_sessions(sessions)