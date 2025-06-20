# tests/test_session_cog.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from bot.cogs.session_cog import SessionCog
from bot.core.identity_service import IdentityService

@pytest.fixture
def mock_session_service():
    svc = MagicMock()
    svc.start_manual_session = AsyncMock()
    svc.end_session = AsyncMock()
    svc.pause_session = AsyncMock()
    return svc

@pytest.fixture
def mock_identity_service():
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
    mock_user_profile = {
        "sdvx_id": "1234-5678", "volforce": 12.345,
        "skill_level": "Lv.08", "total_plays": 100
    }
    mock_identity_service.get_user_by_discord_id.return_value = mock_user_profile
    mock_session_service.start_manual_session.return_value = True 
    with patch("bot.cogs.session_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service, mock_identity_service)
        await cog.checkin.callback(cog, mock_interaction)
        
        kwargs = mock_create_embed.call_args.kwargs
        assert kwargs.get("title") == "✅ Checked In"
        assert "1234-5678" in kwargs.get("description")

@pytest.mark.asyncio
async def test_checkin_failure_already_active(mock_session_service, mock_identity_service, mock_interaction):
    mock_identity_service.get_user_by_discord_id.return_value = {"sdvx_id": "1234"}
    mock_session_service.start_manual_session.return_value = False 
    with patch("bot.cogs.session_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service, mock_identity_service)
        await cog.checkin.callback(cog, mock_interaction)
        assert mock_create_embed.call_args.kwargs.get("theme") == "error"

@pytest.mark.asyncio
async def test_checkin_failure_not_linked(mock_session_service, mock_identity_service, mock_interaction):
    mock_identity_service.get_user_by_discord_id.return_value = None
    with patch("bot.cogs.session_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service, mock_identity_service)
        await cog.checkin.callback(cog, mock_interaction)
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
        assert mock_create_embed.call_args.kwargs.get("title") == "⏸️ Session Paused"

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
        "total_songs_played": 10, "initial_volforce": 10.0, "final_volforce": 10.050
    }
    mock_session_service.end_session.return_value = mock_summary 
    with patch("bot.cogs.session_cog.create_embed", return_value="embed_obj") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service, mock_identity_service)
        await cog.checkout.callback(cog, mock_interaction)

        kwargs = mock_create_embed.call_args.kwargs
        assert kwargs.get("title") == "🏁 Checked Out"
        assert any(field['name'] == 'Total Songs Played' for field in kwargs.get("fields"))
        assert any(field['name'] == 'VF Gained' and field['value'] == '+0.050' for field in kwargs.get("fields"))

@pytest.mark.asyncio
async def test_checkout_no_session_found(mock_session_service, mock_identity_service, mock_interaction):
    mock_session_service.end_session.return_value = None 
    with patch("bot.cogs.session_cog.create_embed", return_value="embed_obj") as mock_create_embed:
        cog = SessionCog(MagicMock(), mock_session_service, mock_identity_service)
        await cog.checkout.callback(cog, mock_interaction)
        assert mock_create_embed.call_args.kwargs.get("title") == "Checkout Failed"