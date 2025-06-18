# tests/test_session_service.py
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta

from bot.core.performance_service import PerformanceService
from bot.core.session_service import SessionService
from bot.eagle_browser import EagleBrowser
from bot.core.identity_service import IdentityService
from bot.core.role_service import RoleService

MOCK_NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

@pytest.fixture
def mock_performance_service():
    svc = MagicMock(spec=PerformanceService)
    svc.identity_service = MagicMock(spec=IdentityService)
    svc.identity_service.get_user_by_discord_id = AsyncMock()
    svc.analyze_new_scores_for_records = MagicMock()
    svc.check_for_vf_milestone = MagicMock()
    svc.get_player_stats_from_cache = MagicMock()
    return svc

@pytest.fixture
def mock_browser():
    browser = MagicMock(spec=EagleBrowser)
    browser.scrape_player_profile = AsyncMock()
    return browser

@pytest.fixture
def mock_role_service():
    svc = MagicMock(spec=RoleService)
    svc.assign_role = AsyncMock()
    svc.remove_role = AsyncMock()
    return svc

@pytest.fixture
def service(mock_performance_service, mock_browser, mock_role_service):
    with patch.object(SessionService, '_blocking_read_sessions', return_value={}) as mock_read_disk, \
         patch.object(SessionService, '_blocking_write_sessions') as mock_write_disk:
        mock_read_disk.return_value = {}
        svc = SessionService("fake_path.json", mock_performance_service, mock_browser, role_service=mock_role_service)
        svc._blocking_read_sessions = mock_read_disk
        svc._blocking_write_sessions = mock_write_disk
        mock_read_disk.reset_mock()
        mock_write_disk.reset_mock()
        yield svc

@pytest.mark.asyncio
async def test_process_new_score_new_session(service, mock_role_service):
    service.sessions = {}
    service._blocking_write_sessions.reset_mock()
    with patch.object(service, '_get_now', return_value=MOCK_NOW):
        await service.process_new_score("user1")
    assert "user1" in service.sessions
    assert service.sessions["user1"]["status"] == "active"
    assert service.sessions["user1"]["type"] == "auto"
    assert service.sessions["user1"]["start_time"] == MOCK_NOW.isoformat()
    service._blocking_write_sessions.assert_called_once()
    mock_role_service.assign_role.assert_awaited_once_with("user1")

@pytest.mark.asyncio
async def test_process_new_score_blocked_by_global_lock(service, mock_role_service):
    service.sessions = {"user1": {"discord_id": "user1", "status": "active"}}
    service._blocking_write_sessions.reset_mock()
    await service.process_new_score("user2")
    service._blocking_write_sessions.assert_not_called()
    assert "user2" not in service.sessions
    mock_role_service.assign_role.assert_not_awaited()
    mock_role_service.remove_role.assert_not_awaited()

@pytest.mark.asyncio
async def test_process_new_score_resumes_session(service, mock_role_service):
    service.sessions = {"user1": {"discord_id": "user1", "status": "on_break"}}
    service._blocking_write_sessions.reset_mock()
    with patch.object(service, '_get_now', return_value=MOCK_NOW):
        await service.process_new_score("user1")
    assert service.sessions["user1"]["status"] == "active"
    assert service.sessions["user1"]["last_activity"] == MOCK_NOW.isoformat()
    service._blocking_write_sessions.assert_called_once()
    mock_role_service.assign_role.assert_awaited_once_with("user1")

@pytest.mark.asyncio
async def test_find_and_end_stale_sessions_active_to_pending(service, mock_role_service):
    now = MOCK_NOW
    stale_time = (now - timedelta(minutes=service.IDLE_TIMEOUT_MIN + 1)).isoformat()
    service.sessions = {"user1": {"status": "active", "last_activity": stale_time}}
    service._blocking_write_sessions.reset_mock()
    with patch.object(service, '_get_now', return_value=now):
        await service.find_and_end_stale_sessions()
    assert service.sessions["user1"]["status"] == "pending_break"
    service._blocking_write_sessions.assert_called_once()
    mock_role_service.remove_role.assert_awaited_once_with("user1")

@pytest.mark.asyncio
async def test_find_and_end_stale_sessions_pending_to_ended(service, mock_role_service):
    now = MOCK_NOW
    stale_time = (now - timedelta(minutes=service.BREAK_TIMEOUT_MIN + 1)).isoformat()
    service.sessions = {"user1": {"discord_id": "user1", "status": "pending_break", "last_activity": stale_time}}
    service._blocking_write_sessions.reset_mock()
    with patch.object(service, '_get_now', return_value=now):
        await service.find_and_end_stale_sessions()
    assert "user1" not in service.sessions
    mock_role_service.remove_role.assert_awaited_once_with("user1")

@pytest.mark.asyncio
async def test_end_session_direct_call(service, mock_role_service):
    service.sessions = {"user1": {"status": "active"}}
    service._blocking_write_sessions.reset_mock()
    with patch.object(service, '_analyze_session_data', new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = {}
        await service.end_session("user1")
    assert "user1" not in service.sessions
    service._blocking_write_sessions.assert_called_once()
    mock_role_service.remove_role.assert_awaited_once_with("user1")

@pytest.mark.asyncio
async def test_start_manual_session_success(service, mock_role_service):
    service.sessions = {}
    service._blocking_write_sessions.reset_mock()
    service.performance_service.identity_service.get_user_by_discord_id.return_value = {"sdvx_id": "12345678", "player_name": "TestPlayer"}
    service.performance_service.get_player_stats_from_cache.return_value = {"volforce": 10.0}
    with patch.object(service, '_get_now', return_value=MOCK_NOW):
        result = await service.start_manual_session("user1")
    assert result is True
    assert "user1" in service.sessions
    assert service.sessions["user1"]["type"] == "manual"
    assert service.sessions["user1"]["status"] == "active"
    assert service.sessions["user1"]["initial_volforce"] == 10.0
    service._blocking_write_sessions.assert_called_once()
    mock_role_service.assign_role.assert_awaited_once_with("user1")

@pytest.mark.asyncio
async def test_start_manual_session_fails_when_locked(service, mock_role_service):
    service.sessions = {"user2": {"discord_id": "user2", "status": "active"}}
    service._blocking_write_sessions.reset_mock()
    result = await service.start_manual_session("user1")
    assert result is False
    service._blocking_write_sessions.assert_not_called()
    assert "user1" not in service.sessions
    mock_role_service.assign_role.assert_not_awaited()
    mock_role_service.remove_role.assert_not_awaited()

@pytest.mark.asyncio
async def test_pause_session_success(service, mock_role_service):
    service.sessions = {"user1": {"status": "active"}}
    service._blocking_write_sessions.reset_mock()
    with patch.object(service, '_get_now', return_value=MOCK_NOW):
        result = await service.pause_session("user1")
    assert result is True
    assert service.sessions["user1"]["status"] == "on_break"
    service._blocking_write_sessions.assert_called_once()
    mock_role_service.remove_role.assert_awaited_once_with("user1")

@pytest.mark.asyncio
async def test_pause_session_fails_if_not_active(service, mock_role_service):
    service.sessions = {"user1": {"status": "on_break"}}
    service._blocking_write_sessions.reset_mock()
    result = await service.pause_session("user1")
    assert result is False
    service._blocking_write_sessions.assert_not_called()
    mock_role_service.assign_role.assert_not_awaited()
    mock_role_service.remove_role.assert_not_awaited()

@pytest.mark.asyncio
async def test_force_checkout_success(service, mock_role_service):
    service.sessions = {"user1_to_checkout": {"status": "any_status"}}
    service._blocking_write_sessions.reset_mock()
    with patch.object(service, '_analyze_session_data', new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = {}
        result = await service.force_checkout("user1_to_checkout")
    assert result is True
    assert "user1_to_checkout" not in service.sessions
    service._blocking_write_sessions.assert_called_once()
    mock_role_service.remove_role.assert_awaited_once_with("user1_to_checkout")

@pytest.mark.asyncio
async def test_force_checkout_no_session(service, mock_role_service):
    service.sessions = {}
    service._blocking_write_sessions.reset_mock()
    result = await service.force_checkout("user_with_no_session")
    assert result is False
    service._blocking_write_sessions.assert_not_called()
    mock_role_service.assign_role.assert_not_awaited()
    mock_role_service.remove_role.assert_not_awaited()

def test_get_session_count(service):
    service.sessions = {"user1": {}, "user2": {}, "user3": {}}
    service._blocking_write_sessions.reset_mock()
    count = service.get_session_count()
    assert count == 3
    service._blocking_write_sessions.assert_not_called()

@pytest.mark.asyncio
async def test_start_manual_session_stores_initial_volforce(service):
    service.sessions = {}
    service._blocking_write_sessions.reset_mock()
    service.performance_service.identity_service.get_user_by_discord_id.return_value = {"sdvx_id": "12345678", "player_name": "TestPlayer"}
    service.performance_service.get_player_stats_from_cache.return_value = {"volforce": 12.34}
    with patch.object(service, '_get_now', return_value=MOCK_NOW):
        result = await service.start_manual_session("user1")
    assert result is True
    assert service.sessions["user1"]["initial_volforce"] == 12.34
    service._blocking_write_sessions.assert_called_once()

@pytest.mark.asyncio
async def test_end_session_returns_summary(service):
    service.sessions = {"user1": {"discord_id": "user1", "start_time": MOCK_NOW.isoformat(), "initial_volforce": 10.0}}
    service._blocking_write_sessions.reset_mock()
    expected_summary = {"player_name": "TestPlayer", "sdvx_id": "12345678", "session_duration_minutes": 0.0, "new_records": ["Song X"], "vf_milestone": "Scarlet I", "initial_volforce": 10.0, "final_volforce": 15.0}
    with patch.object(service, '_analyze_session_data', new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = expected_summary
        summary = await service.end_session("user1")
    assert summary == expected_summary
    assert "user1" not in service.sessions
    service._blocking_write_sessions.assert_called_once()

@pytest.mark.asyncio
async def test_analyze_session_data_success(service, mock_browser):
    discord_id = "test_user_id"
    sdvx_id = "12345678"
    player_name = "TestPlayer"
    initial_vf = 14.500
    final_vf = 15.010
    session_start_time = MOCK_NOW - timedelta(minutes=30)
    service.sessions[discord_id] = {
        "discord_id": discord_id,
        "start_time": session_start_time.isoformat(),
        "initial_volforce": initial_vf
    }
    service.performance_service.identity_service.get_user_by_discord_id.return_value = {"sdvx_id": sdvx_id, "player_name": player_name}
    mock_browser.scrape_player_profile.return_value = {"player_name": player_name, "volforce": final_vf, "recent_plays": [{"song_title": "Song B"}]}
    service.performance_service.analyze_new_scores_for_records.return_value = [{"song_title": "Song B"}]
    service.performance_service.check_for_vf_milestone.return_value = "Scarlet I"

    with patch.object(service, '_get_now', return_value=MOCK_NOW):
        summary = await service._analyze_session_data(discord_id)

    assert summary["player_name"] == player_name
    assert summary["sdvx_id"] == sdvx_id
    assert pytest.approx(summary["session_duration_minutes"], 0.1) == 30.0
    assert summary["new_records"] == ["Song B"]
    
    # --- THIS IS THE CORRECTED PART ---
    assert summary["vf_milestone"] == "Scarlet I"
    service.performance_service.check_for_vf_milestone.assert_called_once_with(initial_vf, final_vf)
    # --- END CORRECTION ---

    assert summary["initial_volforce"] == initial_vf
    assert summary["final_volforce"] == final_vf
    service.performance_service.identity_service.get_user_by_discord_id.assert_awaited_once_with(discord_id)
    mock_browser.scrape_player_profile.assert_awaited_once_with(sdvx_id)
    service.performance_service.analyze_new_scores_for_records.assert_called_once()