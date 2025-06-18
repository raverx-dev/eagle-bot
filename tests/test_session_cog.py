# tests/test_session_cog.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import discord
from bot.cogs.session_cog import SessionCog
from bot.core.identity_service import IdentityService # Import for mocking

@pytest.fixture
def mock_session_service():
    svc = MagicMock()
    svc.start_manual_session = AsyncMock()
    svc.end_session = AsyncMock()
    svc.pause_session = AsyncMock()
    return svc

@pytest.fixture
def mock_identity_service(): # New fixture for the new dependency
    svc = MagicMock(spec=IdentityService)
    svc.get_user_by_discord_id = AsyncMock()
    return svc

@pytest.fixture
def mock_interaction():
    interaction = MagicMock()
    interaction.user.id = 12345
    interaction.response.send_message = AsyncMock()
    return interaction

@pytest.mark.asyncio
async def test_checkin_success(mock_session_service, mock_identity_service, mock_interaction):
    mock_identity_service.get_user_by_discord_id.return_value = {"sdvx_id": "1234"} # User is linked
    mock_session_service.start_manual_session.return_value = True 
    with patch("bot.cogs.session_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service, mock_identity_service)
        await cog.checkin.callback(cog, mock_interaction)

        mock_session_service.start_manual_session.assert_called_once_with(str(mock_interaction.user.id))
        mock_create_embed.assert_called_once()
        assert mock_create_embed.call_args.kwargs.get("theme") == "success"

@pytest.mark.asyncio
async def test_checkin_failure_already_active(mock_session_service, mock_identity_service, mock_interaction):
    mock_identity_service.get_user_by_discord_id.return_value = {"sdvx_id": "1234"} # User is linked
    mock_session_service.start_manual_session.return_value = False 
    with patch("bot.cogs.session_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service, mock_identity_service)
        await cog.checkin.callback(cog, mock_interaction)
        assert mock_create_embed.call_args.kwargs.get("theme") == "error"

# This is a new, additional test for the unlinked case.
@pytest.mark.asyncio
async def test_checkin_failure_not_linked(mock_session_service, mock_identity_service, mock_interaction):
    mock_identity_service.get_user_by_discord_id.return_value = None # User is NOT linked
    with patch("bot.cogs.session_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service, mock_identity_service)
        await cog.checkin.callback(cog, mock_interaction)
        mock_session_service.start_manual_session.assert_not_awaited() # Should not be called
        assert "must link your SDVX ID" in mock_create_embed.call_args.kwargs.get("description")

@pytest.mark.asyncio
async def test_checkout_command_no_summary(mock_session_service, mock_identity_service, mock_interaction):
    mock_session_service.end_session.return_value = None 
    with patch("bot.cogs.session_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service, mock_identity_service)
        await cog.checkout.callback(cog, mock_interaction)
        assert mock_create_embed.call_args.kwargs.get("theme") == "error"
        assert "No active session found" in mock_create_embed.call_args.kwargs.get("description")

@pytest.mark.asyncio
async def test_break_success(mock_session_service, mock_identity_service, mock_interaction):
    mock_session_service.pause_session.return_value = True 
    with patch("bot.cogs.session_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service, mock_identity_service)
        await cog.break_session.callback(cog, mock_interaction)
        assert mock_create_embed.call_args.kwargs.get("theme") == "success"

@pytest.mark.asyncio
async def test_break_failure(mock_session_service, mock_identity_service, mock_interaction):
    mock_session_service.pause_session.return_value = False 
    with patch("bot.cogs.session_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service, mock_identity_service)
        await cog.break_session.callback(cog, mock_interaction)
        assert mock_create_embed.call_args.kwargs.get("theme") == "error"

@pytest.mark.asyncio
async def test_checkout_with_detailed_summary(mock_session_service, mock_identity_service, mock_interaction):
    mock_summary = {
        "player_name": "TestPlayer", "session_duration_minutes": 45.5,
        "initial_volforce": 10.0, "final_volforce": 10.5,
        "new_records": ["Song A", "Song B"], "vf_milestone": "Scarlet I"
    }
    mock_session_service.end_session.return_value = mock_summary 
    with patch("bot.cogs.session_cog.create_embed", return_value="embed_obj") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service, mock_identity_service)
        await cog.checkout.callback(cog, mock_interaction)
        assert mock_create_embed.call_args.kwargs.get("title") == f"Session Summary for {mock_summary['player_name']}"

@pytest.mark.asyncio
async def test_checkout_no_session_found(mock_session_service, mock_identity_service, mock_interaction):
    mock_session_service.end_session.return_value = None 
    with patch("bot.cogs.session_cog.create_embed", return_value="embed_obj") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service, mock_identity_service)
        await cog.checkout.callback(cog, mock_interaction)
        assert mock_create_embed.call_args.kwargs.get("title") == "Checkout Failed"