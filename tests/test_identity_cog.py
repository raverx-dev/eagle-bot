import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import discord
from bot.cogs.identity_cog import IdentityCog

@pytest.fixture
def mock_identity_service():
    svc = MagicMock()
    svc.link_user = AsyncMock() # This method is async
    return svc

@pytest.fixture
def mock_interaction():
    interaction = MagicMock()
    interaction.user.id = 12345
    interaction.response.send_message = AsyncMock()
    return interaction

@pytest.mark.asyncio
@pytest.mark.parametrize("link_result, expected_theme", [(True, "success"), (False, "error")])
async def test_linkid_command(mock_identity_service, mock_interaction, link_result, expected_theme):
    # Correctly set the return value for the AsyncMock
    mock_identity_service.link_user.return_value = link_result
    sdvx_id_arg = "1234-5678"

    with patch("bot.cogs.identity_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = IdentityCog(MagicMock(), mock_identity_service)
        await cog.linkid.callback(cog, mock_interaction, sdvx_id=sdvx_id_arg)

        mock_identity_service.link_user.assert_called_once_with(str(mock_interaction.user.id), sdvx_id_arg)
        mock_create_embed.assert_called_once()
        assert mock_create_embed.call_args.kwargs.get("theme") == expected_theme
        mock_interaction.response.send_message.assert_awaited_once_with(embed="embed", ephemeral=True)