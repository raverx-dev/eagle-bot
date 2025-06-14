import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from bot.utils.notification_service import NotificationService

def test_initialization_success():
    with patch("os.getenv", return_value="12345"):
        mock_bot = MagicMock()
        service = NotificationService(mock_bot)
        assert service.channel_id == 12345
        assert service.bot is mock_bot

def test_initialization_fails_not_set():
    with patch("os.getenv", return_value=None):
        mock_bot = MagicMock()
        with pytest.raises(Exception) as excinfo:
            NotificationService(mock_bot)
        assert str(excinfo.value) == "ADMIN_ALERT_CHANNEL_ID environment variable is not set."

def test_initialization_fails_invalid_integer():
    with patch("os.getenv", return_value="abc"):
        mock_bot = MagicMock()
        with pytest.raises(Exception) as excinfo:
            NotificationService(mock_bot)
        assert str(excinfo.value) == "ADMIN_ALERT_CHANNEL_ID must be an integer."

@pytest.mark.asyncio
async def test_send_admin_alert_success():
    with patch("os.getenv", return_value="12345"):
        mock_bot = MagicMock()
        mock_channel = MagicMock()
        mock_channel.send = AsyncMock()
        mock_bot.get_channel.return_value = mock_channel
        service = NotificationService(mock_bot)
        await service.send_admin_alert("Hello Admins!")
        mock_bot.get_channel.assert_called_once_with(12345)
        mock_channel.send.assert_awaited_once_with("Hello Admins!")

@pytest.mark.asyncio
async def test_send_admin_alert_channel_not_found(capfd):
    with patch("os.getenv", return_value="12345"):
        mock_bot = MagicMock()
        mock_bot.get_channel.return_value = None
        service = NotificationService(mock_bot)
        await service.send_admin_alert("No channel")
        mock_bot.get_channel.assert_called_once_with(12345)
        # No send should be called
        # Check output for print statement
        out, _ = capfd.readouterr()
        assert f"Admin alert channel with ID {service.channel_id} not found." in out