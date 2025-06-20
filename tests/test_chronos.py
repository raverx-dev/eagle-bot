# tests/test_chronos.py
import pytest
import functools
from unittest.mock import MagicMock, AsyncMock

from bot.utils.chronos import Chronos
from bot.utils.error_handler import ScrapeErrorHandler

@pytest.fixture
def mock_services():
    system_service = MagicMock()
    identity_service = MagicMock()
    identity_service.update_player_cache = AsyncMock()
    identity_service._read_users = AsyncMock(return_value={})
    session_service = MagicMock()
    session_service.find_and_end_stale_sessions = AsyncMock()
    session_service.process_new_score = AsyncMock()
    error_handler = MagicMock(spec=ScrapeErrorHandler)
    
    # This mock decorator now correctly returns a pass-through function
    def passthrough_decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper

    error_handler.handle_scrape_failures.return_value = passthrough_decorator
    return system_service, identity_service, session_service, error_handler

@pytest.mark.asyncio
async def test_tick_during_open_hours(mock_services):
    system_service, identity_service, session_service, error_handler = mock_services
    system_service.is_within_arcade_hours.return_value = True
    
    chronos = Chronos(system_service, identity_service, session_service, error_handler)

    await chronos._tick()
    identity_service.update_player_cache.assert_awaited_once()
    session_service.find_and_end_stale_sessions.assert_awaited_once()

@pytest.mark.asyncio
async def test_tick_during_closed_hours(mock_services):
    system_service, identity_service, session_service, error_handler = mock_services
    system_service.is_within_arcade_hours.return_value = False
    chronos = Chronos(system_service, identity_service, session_service, error_handler)
    await chronos._tick()
    identity_service.update_player_cache.assert_not_awaited()

@pytest.mark.asyncio
async def test_tick_handles_service_exception(mock_services):
    system_service, identity_service, session_service, error_handler = mock_services
    
    # FIX: The decorator factory MUST be a regular `def`, not `async def`.
    def decorator_that_raises(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                raise e
        return wrapper
    
    error_handler.handle_scrape_failures.return_value = decorator_that_raises
    
    system_service.is_within_arcade_hours.return_value = True
    identity_service.update_player_cache.side_effect = Exception("fail")
    
    chronos = Chronos(system_service, identity_service, session_service, error_handler)
    
    # Now this will work as intended, catching the "fail" exception.
    with pytest.raises(Exception, match="fail"):
        await chronos._tick()
    
    identity_service.update_player_cache.assert_awaited_once()
    session_service.find_and_end_stale_sessions.assert_not_awaited()

@pytest.mark.asyncio
async def test_check_for_new_scores_logic(mock_services):
    system_service, identity_service, session_service, error_handler = mock_services
    chronos = Chronos(system_service, identity_service, session_service, error_handler)
    
    identity_service._read_users.return_value = {
        "123": {"discord_id": "user1", "recent_plays": [{"timestamp": "ts_initial"}]}
    }
    await chronos._check_for_new_scores()
    session_service.process_new_score.assert_not_awaited()

    identity_service._read_users.return_value = {
        "123": {"discord_id": "user1", "recent_plays": [{"timestamp": "ts_new"}]}
    }
    await chronos._check_for_new_scores()
    session_service.process_new_score.assert_awaited_once_with("user1")