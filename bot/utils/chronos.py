import asyncio
from bot.core.system_service import SystemService
from bot.core.identity_service import IdentityService
from bot.core.session_service import SessionService

class Chronos:
    def __init__(self, system_service: SystemService, identity_service: IdentityService, session_service: SessionService, interval_seconds: int = 60):
        self.system_service = system_service
        self.identity_service = identity_service
        self.session_service = session_service
        self.interval_seconds = interval_seconds

    async def start(self):
        while True:
            await self._tick()
            await asyncio.sleep(self.interval_seconds)

    async def _tick(self):
        if not self.system_service.is_within_arcade_hours():
            return
        try:
            await self.identity_service.update_player_cache()
            await self.session_service.find_and_end_stale_sessions()
        except Exception as e:
            print(f"Chronos tick error: {e}")
