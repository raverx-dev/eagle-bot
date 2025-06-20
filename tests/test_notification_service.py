# tests/test_notification_service.py

import pytest
import discord
from unittest.mock import patch, MagicMock, AsyncMock

from bot.utils.notification_service import NotificationService

@pytest.fixture
def mock_bot():
    """A fixture to create a mock bot with async capabilities."""
    bot = MagicMock(spec=discord.Client)
    bot.get_channel = MagicMock()
    bot.fetch_channel = AsyncMock()
    bot.fetch_user = AsyncMock()
    return bot

# --- Tests for __init__ ---

def test_initialization_all_channels_set(mock_bot):
    with patch("os.getenv") as mock_getenv:
        mock_getenv.side_effect = lambda key, default=None: {
            "ADMIN_ALERT_CHANNEL_ID": "123",
            "SESSION_LOG_CHANNEL_ID": "456",
            "MILESTONE_CHANNEL_ID": "789"
        }.get(key, default)
        service = NotificationService(mock_bot)
        assert service.admin_channel_id == 123
        assert service.session_log_channel_id == 456
        assert service.milestone_channel_id == 789

def test_initialization_logs_warning_if_not_set(mock_bot, caplog):
    with patch("os.getenv", return_value=None):
        NotificationService(mock_bot)
        assert "MILESTONE_CHANNEL_ID not set" in caplog.text

def test_initialization_logs_error_if_invalid(mock_bot, caplog):
    with patch("os.getenv", return_value="abc"):
        NotificationService(mock_bot)
        assert "not a valid integer" in caplog.text

# --- Tests for send_admin_alert ---

@pytest.mark.asyncio
async def test_send_admin_alert_success(mock_bot):
    with patch("os.getenv", return_value="123"):
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.send = AsyncMock()
        mock_bot.get_channel.return_value = mock_channel

        service = NotificationService(mock_bot)
        await service.send_admin_alert("Test Alert")
        mock_channel.send.assert_awaited_once_with("Test Alert")

@pytest.mark.asyncio
async def test_send_admin_alert_channel_not_found(mock_bot, caplog):
    with patch("os.getenv", return_value="123"):
        mock_bot.get_channel.return_value = None
        mock_bot.fetch_channel.return_value = None

        service = NotificationService(mock_bot)
        await service.send_admin_alert("No channel")
        assert "Could not find admin alert channel with ID 123" in caplog.text

# --- Tests for send_session_reminder_dm ---

@pytest.mark.asyncio
async def test_send_session_reminder_dm_success(mock_bot):
    with patch("os.getenv"), patch("bot.utils.notification_service.create_embed"):
        mock_user = MagicMock(spec=discord.User)
        mock_user.send = AsyncMock()
        mock_bot.fetch_user.return_value = mock_user

        service = NotificationService(mock_bot)
        result = await service.send_session_reminder_dm(67890)
        mock_user.send.assert_awaited_once()
        assert result is True

@pytest.mark.asyncio
async def test_send_session_reminder_dm_fails_on_forbidden(mock_bot):
    with patch("os.getenv"):
        mock_user = MagicMock(spec=discord.User)
        mock_user.send = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "DMs disabled"))
        mock_bot.fetch_user.return_value = mock_user

        service = NotificationService(mock_bot)
        result = await service.send_session_reminder_dm(67890)
        assert result is False

# --- Tests for post_session_summary ---

@pytest.mark.asyncio
async def test_post_session_summary_success(mock_bot):
    with patch("os.getenv") as mock_getenv, patch("bot.utils.notification_service.create_embed"):
        mock_getenv.side_effect = lambda key, default=None: {"SESSION_LOG_CHANNEL_ID": "456"}.get(key, default)
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.send = AsyncMock()
        mock_bot.get_channel.return_value = mock_channel

        service = NotificationService(mock_bot)
        await service.post_session_summary({"player_name": "Test Player"})
        mock_channel.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_post_session_summary_no_channel_id(mock_bot, caplog):
    with patch("os.getenv", return_value=None):
        service = NotificationService(mock_bot)
        caplog.clear()  # clear init warnings
        await service.post_session_summary({"player_name": "Test Player"})
        assert "channel not configured" in caplog.text

# --- Tests for post_vf_milestone_announcement ---

@pytest.mark.asyncio
async def test_post_vf_milestone_announcement_success(mock_bot):
    with patch("os.getenv") as mock_getenv, patch("bot.utils.notification_service.create_embed"):
        mock_getenv.side_effect = lambda key, default=None: {"MILESTONE_CHANNEL_ID": "789"}.get(key, default)
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.send = AsyncMock()
        mock_bot.get_channel.return_value = mock_channel

        service = NotificationService(mock_bot)
        await service.post_vf_milestone_announcement("Player1", "Crimson I")
        mock_channel.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_post_vf_milestone_announcement_no_channel_id(mock_bot, caplog):
    with patch("os.getenv", return_value=None):
        service = NotificationService(mock_bot)
        caplog.clear()  # clear init warnings
        await service.post_vf_milestone_announcement("Player1", "Crimson I")
        assert "channel not configured" in caplog.text
