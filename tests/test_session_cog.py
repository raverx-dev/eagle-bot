import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import discord
from bot.cogs.session_cog import SessionCog

@pytest.fixture
def mock_session_service():
    return MagicMock()

@pytest.fixture
def mock_interaction():
    interaction = MagicMock()
    interaction.user.id = 12345
    interaction.response.send_message = AsyncMock()
    return interaction

@pytest.mark.asyncio
async def test_checkin_success(mock_session_service, mock_interaction):
    mock_session_service.start_manual_session.return_value = True
    with patch("bot.cogs.session_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service)
        # Call the .callback of the command, passing the cog instance as self
        await cog.checkin.callback(cog, mock_interaction)
        
        mock_session_service.start_manual_session.assert_called_once_with(12345)
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        assert kwargs.get("theme") == "success"
        mock_interaction.response.send_message.assert_awaited_once_with(embed="embed", ephemeral=True)

@pytest.mark.asyncio
async def test_checkin_failure(mock_session_service, mock_interaction):
    mock_session_service.start_manual_session.return_value = False
    with patch("bot.cogs.session_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service)
        await cog.checkin.callback(cog, mock_interaction)
        
        mock_session_service.start_manual_session.assert_called_once_with(12345)
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        assert kwargs.get("theme") == "error"
        mock_interaction.response.send_message.assert_awaited_once_with(embed="embed", ephemeral=True)

@pytest.mark.asyncio
async def test_checkout_command(mock_session_service, mock_interaction):
    with patch("bot.cogs.session_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service)
        await cog.checkout.callback(cog, mock_interaction)
        
        mock_session_service.end_session.assert_called_once_with(12345)
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        assert kwargs.get("theme") == "success"
        mock_interaction.response.send_message.assert_awaited_once_with(embed="embed", ephemeral=True)

@pytest.mark.asyncio
async def test_break_success(mock_session_service, mock_interaction):
    mock_session_service.pause_session.return_value = True
    with patch("bot.cogs.session_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service)
        await cog.break_session.callback(cog, mock_interaction)
        
        mock_session_service.pause_session.assert_called_once_with(12345)
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        assert kwargs.get("theme") == "success"
        mock_interaction.response.send_message.assert_awaited_once_with(embed="embed", ephemeral=True)

@pytest.mark.asyncio
async def test_break_failure(mock_session_service, mock_interaction):
    mock_session_service.pause_session.return_value = False
    with patch("bot.cogs.session_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service)
        await cog.break_session.callback(cog, mock_interaction)
        
        mock_session_service.pause_session.assert_called_once_with(12345)
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        assert kwargs.get("theme") == "error"
        mock_interaction.response.send_message.assert_awaited_once_with(embed="embed", ephemeral=True)