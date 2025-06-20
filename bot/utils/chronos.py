# bot/utils/chronos.py
import asyncio
from bot.config import log
from bot.core.system_service import SystemService
from bot.core.identity_service import IdentityService
from bot.core.session_service import SessionService
from bot.utils.error_handler import ScrapeErrorHandler # Import new dependency

class Chronos:
    # Add error_handler to the constructor
    def __init__(self, system_service: SystemService, identity_service: IdentityService, session_service: SessionService, error_handler: ScrapeErrorHandler, interval_seconds: int = 60):
        self.system_service = system_service
        self.identity_service = identity_service
        self.session_service = session_service
        self.interval_seconds = interval_seconds
        self.last_known_play_timestamps = {}
        self._is_first_tick = True
        self.error_handler = error_handler

        # Apply the decorator to the _tick method instance
        self._tick = self.error_handler.handle_scrape_failures()(self._tick)

    async def start(self):
        while True:
            await self._tick()
            await asyncio.sleep(self.interval_seconds)

    async def _check_for_new_scores(self):
        all_users = await self.identity_service._read_users()

        if self._is_first_tick:
            log.info("CHRONOS: First tick, populating initial play timestamps...")
            for sdvx_id, user_data in all_users.items():
                if user_data.get("recent_plays"):
                    latest_play_timestamp = user_data["recent_plays"][0].get("timestamp")
                    if latest_play_timestamp:
                        self.last_known_play_timestamps[sdvx_id] = latest_play_timestamp
            self._is_first_tick = False
            log.info(f"CHRONOS: Initialized timestamps for {len(self.last_known_play_timestamps)} players.")
            return

        for sdvx_id, user_data in all_users.items():
            discord_id = user_data.get("discord_id")
            recent_plays = user_data.get("recent_plays")

            if not discord_id or not recent_plays: continue
            latest_play_timestamp = recent_plays[0].get("timestamp")
            if not latest_play_timestamp: continue
            
            last_known_timestamp = self.last_known_play_timestamps.get(sdvx_id)
            if latest_play_timestamp != last_known_timestamp:
                log.info(f"CHRONOS: New score detected for player {sdvx_id} ({user_data.get('player_name')}).")
                try:
                    await self.session_service.process_new_score(discord_id)
                    self.last_known_play_timestamps[sdvx_id] = latest_play_timestamp
                    log.info(f"CHRONOS: Session processed and timestamp updated for {sdvx_id}.")
                except Exception as e:
                    log.error(f"CHRONOS: Error processing new score for {discord_id}: {e}", exc_info=True)

    async def _tick(self):
        # The old try/except block is removed from here. The decorator now handles failures.
        if not self.system_service.is_within_arcade_hours():
            return
        
        await self.identity_service.update_player_cache()
        await self._check_for_new_scores()
        await self.session_service.find_and_end_stale_sessions()