import json
from datetime import datetime, time, timedelta
import pytz

class SystemService:
    def __init__(self, schedule_file_path: str):
        try:
            with open(schedule_file_path, "r") as f:
                self.schedule = json.load(f)
        except FileNotFoundError:
            self.schedule = {}

    def _get_now(self) -> datetime:
        """Returns the current time in UTC. This can be mocked for testing."""
        return datetime.now(pytz.utc)

    def is_within_arcade_hours(self) -> bool:
        now_utc = self._get_now()
        now_time = now_utc.time()

        # --- Check today's schedule ---
        today_str = now_utc.strftime("%A").lower()
        today_schedule = self.schedule.get(today_str, {})
        
        if today_schedule.get("open"):
            open_time = time.fromisoformat(today_schedule["open"])
            close_time = time.fromisoformat(today_schedule["close"])

            # Case 1: Same-day session (e.g., 10:00-20:00)
            if open_time <= close_time:
                if open_time <= now_time < close_time:
                    return True
            # Case 2: Overnight session (e.g., 22:00-02:00)
            else:
                if now_time >= open_time:
                    return True

        # --- Check yesterday's schedule for overnight spillover ---
        yesterday_utc = now_utc - timedelta(days=1)
        yesterday_str = yesterday_utc.strftime("%A").lower()
        yesterday_schedule = self.schedule.get(yesterday_str, {})
        
        if yesterday_schedule.get("open"):
            open_time = time.fromisoformat(yesterday_schedule["open"])
            close_time = time.fromisoformat(yesterday_schedule["close"])
            
            # Case 3: Yesterday had an overnight session, check if we are before the close time
            if open_time > close_time:
                if now_time < close_time:
                    return True
        
        return False