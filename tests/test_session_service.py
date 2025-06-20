# tests/test_session_service.py
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta

from bot.utils.notification_service import NotificationService
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
def mock_notification_service():
    svc = MagicMock(spec=NotificationService)
    svc.send_session_reminder_dm = AsyncMock(return_value=True)
    svc.post_session_summary = AsyncMock()
    svc.post_vf_milestone_announcement = AsyncMock()
    return svc

@pytest.fixture
def service(mock_performance_service, mock_browser, mock_role_service, mock_notification_service):
    with patch.object(SessionService, '_blocking_read_sessions', return_value={}), \
         patch.object(SessionService, '_blocking_write_sessions'):
        svc = SessionService(
            "fake_path.json",
            performance_service=mock_performance_service,
            browser=mock_browser,
            role_service=mock_role_service,
            notification_service=mock_notification_service
        )
        yield svc

@pytest.mark.asyncio
async def test_process_new_score_new_session(service, mock_role_service):
    """FIX: Add mock return value for the new get_user_by_discord_id call."""
    service.sessions = {}
    # The new code calls get_user_by_discord_id, so we mock its return value for this test
    service.performance_service.identity_service.get_user_by_discord_id.return_value = {"volforce": 15.0}
    
    with patch.object(service, '_get_now', return_value=MOCK_NOW):
        await service.process_new_score("user1")

    assert "user1" in service.sessions
    assert service.sessions["user1"]["reminder_sent"] is False
    assert service.sessions["user1"]["initial_volforce"] == 15.0
    mock_role_service.assign_role.assert_awaited_once_with("user1")

# --- All other tests remain unchanged ---

@pytest.mark.asyncio
async def test_find_and_end_stale_sessions_active_to_pending(service, mock_role_service, mock_notification_service):
    now = MOCK_NOW
    stale_time = (now - timedelta(minutes=service.IDLE_TIMEOUT_MIN + 1)).isoformat()
    user_id_str = "12345"
    service.sessions = {user_id_str: {"status": "active", "last_activity": stale_time, "reminder_sent": False}}
    with patch.object(service, '_get_now', return_value=now):
        await service.find_and_end_stale_sessions()
    assert service.sessions[user_id_str]["status"] == "pending_break"
    mock_notification_service.send_session_reminder_dm.assert_awaited_once_with(int(user_id_str))

@pytest.mark.asyncio
async def test_find_and_end_stale_sessions_pending_to_ended(service, mock_notification_service):
    now = MOCK_NOW
    stale_time = (now - timedelta(minutes=service.BREAK_TIMEOUT_MIN + 1)).isoformat()
    user_id_str = "12345"
    service.sessions = {user_id_str: {"status": "pending_break", "last_activity": stale_time}}
    mock_summary = {"player_name": "Test Player"}
    with patch.object(service, '_analyze_session_data', new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_summary
        with patch.object(service, '_get_now', return_value=now):
            await service.find_and_end_stale_sessions()
    assert user_id_str not in service.sessions
    mock_notification_service.post_session_summary.assert_awaited_once_with(mock_summary)

@pytest.mark.asyncio
async def test_find_and_end_stale_sessions_on_break_to_ended(service, mock_notification_service):
    now = MOCK_NOW
    stale_time = (now - timedelta(hours=service.ON_BREAK_TIMEOUT_HOURS + 1)).isoformat()
    user_id_str = "54321"
    service.sessions = {user_id_str: {"status": "on_break", "last_activity": stale_time}}
    mock_summary = {"player_name": "On Break Player"}
    with patch.object(service, '_analyze_session_data', new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_summary
        with patch.object(service, '_get_now', return_value=now):
            await service.find_and_end_stale_sessions()
    assert user_id_str not in service.sessions
    mock_notification_service.post_session_summary.assert_awaited_once_with(mock_summary)

@pytest.mark.asyncio
async def test_start_manual_session_success(service, mock_role_service):
    service.sessions = {}
    service.performance_service.identity_service.get_user_by_discord_id.return_value = {"volforce": 10.0}
    with patch.object(service, '_get_now', return_value=MOCK_NOW):
        await service.start_manual_session("user1")
    assert "user1" in service.sessions
    assert service.sessions["user1"]["reminder_sent"] is False
    mock_role_service.assign_role.assert_awaited_once_with("user1")

@pytest.mark.asyncio
async def test_process_new_score_blocked_by_global_lock(service):
    service.sessions = {"user1": {"discord_id": "user1", "status": "active"}}
    await service.process_new_score("user2")
    assert "user2" not in service.sessions

@pytest.mark.asyncio
async def test_process_new_score_resumes_session(service, mock_role_service):
    service.sessions = {"user1": {"discord_id": "user1", "status": "on_break"}}
    with patch.object(service, '_get_now', return_value=MOCK_NOW):
        await service.process_new_score("user1")
    assert service.sessions["user1"]["status"] == "active"
    mock_role_service.assign_role.assert_awaited_once_with("user1")

@pytest.mark.asyncio
async def test_end_session_direct_call(service, mock_role_service):
    with patch.object(service, '_analyze_session_data', new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = {}
        service.sessions = {"user1": {"status": "active"}}
        await service.end_session("user1")
    assert "user1" not in service.sessions
    mock_role_service.remove_role.assert_awaited_once_with("user1")

@pytest.mark.asyncio
async def test_start_manual_session_fails_when_locked(service):
    service.sessions = {"user2": {"discord_id": "user2", "status": "active"}}
    result = await service.start_manual_session("user1")
    assert result is False

@pytest.mark.asyncio
async def test_pause_session_success(service, mock_role_service):
    service.sessions = {"user1": {"status": "active"}}
    with patch.object(service, '_get_now', return_value=MOCK_NOW):
        result = await service.pause_session("user1")
    assert result is True
    assert service.sessions["user1"]["status"] == "on_break"
    mock_role_service.remove_role.assert_awaited_once_with("user1")

@pytest.mark.asyncio
async def test_pause_session_fails_if_not_active(service):
    service.sessions = {"user1": {"status": "on_break"}}
    result = await service.pause_session("user1")
    assert result is False

@pytest.mark.asyncio
async def test_force_checkout_success(service):
    service.sessions = {"user1_to_checkout": {"status": "any_status"}}
    with patch.object(service, 'end_session', new_callable=AsyncMock) as mock_end:
        result = await service.force_checkout("user1_to_checkout")
    assert result is True
    mock_end.assert_awaited_once_with("user1_to_checkout")

@pytest.mark.asyncio
async def test_force_checkout_no_session(service):
    service.sessions = {}
    result = await service.force_checkout("user_with_no_session")
    assert result is False

def test_get_session_count(service):
    service.sessions = {"user1": {}, "user2": {}, "user3": {}}
    assert service.get_session_count() == 3

@pytest.mark.asyncio
async def test_start_manual_session_stores_initial_volforce(service):
    service.sessions = {}
    service.performance_service.identity_service.get_user_by_discord_id.return_value = {"volforce": 12.34}
    with patch.object(service, '_get_now', return_value=MOCK_NOW):
        await service.start_manual_session("user1")
    assert service.sessions["user1"]["initial_volforce"] == 12.34

@pytest.mark.asyncio
async def test_end_session_returns_summary(service):
    service.sessions = {"user1": {}}
    expected_summary = {"player_name": "TestPlayer"}
    with patch.object(service, '_analyze_session_data', new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = expected_summary
        summary = await service.end_session("user1")
    assert summary == expected_summary

@pytest.mark.asyncio
async def test_analyze_session_data_success(service, mock_notification_service):
    discord_id, sdvx_id, player_name = "test_user_id", "12345678", "TestPlayer"
    initial_vf, final_vf, milestone_name = 14.500, 15.010, "Scarlet I"
    service.sessions[discord_id] = {"start_time": (MOCK_NOW - timedelta(minutes=30)).isoformat(), "initial_volforce": initial_vf}
    service.performance_service.identity_service.get_user_by_discord_id.return_value = {
        "sdvx_id": sdvx_id, "player_name": player_name, "volforce": final_vf, "recent_plays": []
    }
    service.performance_service.check_for_vf_milestone.return_value = milestone_name
    with patch.object(service, '_get_now', return_value=MOCK_NOW):
        summary = await service._analyze_session_data(discord_id)
    assert summary["vf_milestone"] == milestone_name
    mock_notification_service.post_vf_milestone_announcement.assert_awaited_once_with(player_name, milestone_name)