import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from bot.utils.chronos import Chronos

@pytest.fixture
def mock_services():
    system_service = MagicMock()
    identity_service = MagicMock()
    identity_service.update_player_cache = AsyncMock()
    session_service = MagicMock()
    session_service.find_and_end_stale_sessions = AsyncMock()
    return system_service, identity_service, session_service

@pytest.mark.asyncio
async def test_tick_during_open_hours(mock_services):
    system_service, identity_service, session_service = mock_services
    system_service.is_within_arcade_hours.return_value = True
    chronos = Chronos(system_service, identity_service, session_service)
    await chronos._tick()
    identity_service.update_player_cache.assert_awaited_once()
    session_service.find_and_end_stale_sessions.assert_awaited_once()

@pytest.mark.asyncio
async def test_tick_during_closed_hours(mock_services):
    system_service, identity_service, session_service = mock_services
    system_service.is_within_arcade_hours.return_value = False
    chronos = Chronos(system_service, identity_service, session_service)
    await chronos._tick()
    identity_service.update_player_cache.assert_not_awaited()
    session_service.find_and_end_stale_sessions.assert_not_awaited()

@pytest.mark.asyncio
async def test_tick_handles_service_exception(mock_services, capsys):
    system_service, identity_service, session_service = mock_services
    system_service.is_within_arcade_hours.return_value = True
    identity_service.update_player_cache.side_effect = Exception("fail")
    chronos = Chronos(system_service, identity_service, session_service)
    await chronos._tick()
    identity_service.update_player_cache.assert_awaited_once()
    session_service.find_and_end_stale_sessions.assert_not_awaited()
    captured = capsys.readouterr()
    assert "Chronos tick error: fail" in captured.out
