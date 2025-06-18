import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from bot.cogs.admin_cog import AdminCog

@pytest.fixture
def mock_session_service():
    svc = MagicMock()
    svc.get_session_count = MagicMock() # This method is synchronous, no AsyncMock needed here
    svc.force_checkout = AsyncMock() # This method is async
    return svc

@pytest.fixture
def mock_identity_service():
    svc = MagicMock()
    svc.force_unlink = AsyncMock() # This method is async
    return svc

@pytest.fixture
def mock_error_handler():
    return MagicMock()

@pytest.fixture
def mock_interaction():
    interaction = MagicMock()
    interaction.response.send_message = AsyncMock()
    return interaction

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 12345
    user.display_name = "TestUser"
    return user

@pytest.mark.asyncio
@pytest.mark.parametrize("system_is_down, session_count, expected_status, expected_count", [
    (False, 2, "UP", "2"),
    (True, 0, "DOWN", "0"),
])
async def test_botstatus(mock_session_service, mock_identity_service, mock_error_handler, mock_interaction, system_is_down, session_count, expected_status, expected_count):
    mock_error_handler.system_is_down = system_is_down
    mock_session_service.get_session_count.return_value = session_count
    with patch("bot.cogs.admin_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = AdminCog(MagicMock(), mock_session_service, mock_identity_service, mock_error_handler)
        await cog.botstatus.callback(cog, mock_interaction)

        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        desc = kwargs.get("description", "")
        assert expected_status in desc
        assert expected_count in desc
        mock_interaction.response.send_message.assert_awaited_once_with(embed="embed", ephemeral=True)

@pytest.mark.asyncio
@pytest.mark.parametrize("force_result, expected_theme", [
    (True, "success"),
    (False, "error"),
])
async def test_force_checkout(mock_session_service, mock_identity_service, mock_error_handler, mock_interaction, mock_user, force_result, expected_theme):
    # Correctly set the return value for the AsyncMock
    mock_session_service.force_checkout.return_value = force_result
    with patch("bot.cogs.admin_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = AdminCog(MagicMock(), mock_session_service, mock_identity_service, mock_error_handler)
        await cog.force_checkout.callback(cog, mock_interaction, mock_user)

        mock_session_service.force_checkout.assert_called_once_with(str(mock_user.id))
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        assert kwargs.get("theme") == expected_theme
        mock_interaction.response.send_message.assert_awaited_once_with(embed="embed", ephemeral=True)

@pytest.mark.asyncio
@pytest.mark.parametrize("force_result, expected_theme", [
    (True, "success"),
    (False, "error"),
])
async def test_force_unlink(mock_session_service, mock_identity_service, mock_error_handler, mock_interaction, mock_user, force_result, expected_theme):
    # Correctly set the return value for the AsyncMock
    mock_identity_service.force_unlink.return_value = force_result
    with patch("bot.cogs.admin_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = AdminCog(MagicMock(), mock_session_service, mock_identity_service, mock_error_handler)
        await cog.force_unlink.callback(cog, mock_interaction, mock_user)

        mock_identity_service.force_unlink.assert_called_once_with(str(mock_user.id))
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        assert kwargs.get("theme") == expected_theme
        mock_interaction.response.send_message.assert_awaited_once_with(embed="embed", ephemeral=True)