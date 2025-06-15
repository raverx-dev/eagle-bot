import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

# Assuming PerformanceService is in this path, even if it's a placeholder
from bot.core.performance_service import PerformanceService
from bot.core.session_service import SessionService

# A consistent, timezone-AWARE time for all tests to use as "now"
MOCK_NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_performance_service():
    """A mock for the PerformanceService dependency."""
    return MagicMock()


@pytest.fixture
def service(mock_performance_service):
    """Provides a SessionService instance for testing."""
    # The file I/O methods will be patched directly on the instance in each test
    return SessionService("fake_path.json", mock_performance_service)


def test_process_new_score_new_session(service):
    """Tests that a new session is created for a new score."""
    with patch.object(service, '_read_sessions', return_value={}), \
         patch.object(service, '_write_sessions') as mock_write, \
         patch.object(service, '_get_active_session', return_value=None), \
         patch.object(service, '_get_now', return_value=MOCK_NOW):
        
        service.process_new_score("user1")

        written_data = mock_write.call_args[0][0]
        assert "user1" in written_data
        assert written_data["user1"]["status"] == "active"
        assert written_data["user1"]["start_time"] == MOCK_NOW.isoformat()


def test_process_new_score_blocked_by_global_lock(service):
    """Tests that a new score is ignored if another session is active."""
    active_session = {"discord_id": "user1", "status": "active"}
    
    with patch.object(service, '_get_active_session', return_value=active_session), \
         patch.object(service, '_write_sessions') as mock_write:

        service.process_new_score("user2")
        mock_write.assert_not_called()


def test_process_new_score_resumes_session(service):
    """Tests that a new score resumes a session that was on break."""
    initial_sessions = {"user1": {"discord_id": "user1", "status": "on_break"}}
    
    with patch.object(service, '_read_sessions', return_value=initial_sessions), \
         patch.object(service, '_write_sessions') as mock_write, \
         patch.object(service, '_get_active_session', return_value=None), \
         patch.object(service, '_get_now', return_value=MOCK_NOW):

        service.process_new_score("user1")
        
        written_data = mock_write.call_args[0][0]
        assert written_data["user1"]["status"] == "active"
        assert written_data["user1"]["last_activity"] == MOCK_NOW.isoformat()


@pytest.mark.asyncio
async def test_find_and_end_stale_sessions_active_to_pending(service):
    """Tests that an idle 'active' session becomes 'pending_break'."""
    stale_time = (MOCK_NOW - timedelta(minutes=11)).isoformat()
    initial_sessions = {"user1": {"status": "active", "last_activity": stale_time}}

    with patch.object(service, '_read_sessions', return_value=initial_sessions), \
         patch.object(service, '_write_sessions') as mock_write, \
         patch.object(service, '_get_now', return_value=MOCK_NOW):

        await service.find_and_end_stale_sessions()
        
        written_data = mock_write.call_args[0][0]
        assert written_data["user1"]["status"] == "pending_break"


@pytest.mark.asyncio
async def test_find_and_end_stale_sessions_pending_to_ended(service):
    """Tests that an idle 'pending_break' session is removed."""
    stale_time = (MOCK_NOW - timedelta(minutes=6)).isoformat()
    initial_sessions = {"user1": {"status": "pending_break", "last_activity": stale_time}}
    
    with patch.object(service, '_read_sessions', return_value=initial_sessions), \
         patch.object(service, '_write_sessions') as mock_write, \
         patch.object(service, '_get_now', return_value=MOCK_NOW):

        await service.find_and_end_stale_sessions()
        
        written_data = mock_write.call_args[0][0]
        assert "user1" not in written_data


def test_end_session_direct_call(service):
    """Tests that a direct call to end_session removes the session."""
    initial_sessions = {"user1": {"status": "active"}}

    with patch.object(service, '_read_sessions', return_value=initial_sessions), \
         patch.object(service, '_write_sessions') as mock_write:

        service.end_session("user1")
        
        written_data = mock_write.call_args[0][0]
        assert "user1" not in written_data