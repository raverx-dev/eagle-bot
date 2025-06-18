import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from bot.cogs.performance_cog import PerformanceCog

@pytest.fixture
def mock_performance_service():
    svc = MagicMock()
    svc.get_player_stats_from_cache = MagicMock() # This is a synchronous read from cache
    svc.get_arcade_leaderboard_from_cache = MagicMock() # This is a synchronous read from cache
    return svc

@pytest.fixture
def mock_identity_service():
    svc = MagicMock()
    svc.get_user_by_discord_id = AsyncMock() # This method is async
    return svc

@pytest.fixture
def mock_interaction():
    interaction = MagicMock()
    interaction.user.id = 12345
    interaction.user.display_name = "TestUser"
    interaction.response.send_message = AsyncMock()
    return interaction

@pytest.mark.asyncio
async def test_stats_success(mock_performance_service, mock_identity_service, mock_interaction):
    # Correctly set the return value for the AsyncMock
    mock_identity_service.get_user_by_discord_id.return_value = {"sdvx_id": "9999"} # It returns a dict, no need for AsyncMock wrapper here, as it's awaited in the cog
    mock_performance_service.get_player_stats_from_cache.return_value = {
        "player_name": "TestUser", "volforce": 12.34, "rank": 5
    }
    with patch("bot.cogs.performance_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = PerformanceCog(MagicMock(), mock_performance_service, mock_identity_service)
        await cog.stats.callback(cog, mock_interaction)

        mock_identity_service.get_user_by_discord_id.assert_called_once_with(str(12345))
        mock_performance_service.get_player_stats_from_cache.assert_called_once_with("9999")
        mock_create_embed.assert_called_once()
        assert "TestUser" in mock_create_embed.call_args.kwargs.get("description", "")

@pytest.mark.asyncio
async def test_stats_user_not_linked(mock_performance_service, mock_identity_service, mock_interaction):
    # Correctly set the return value for the AsyncMock
    mock_identity_service.get_user_by_discord_id.return_value = None # It returns None, no need for AsyncMock wrapper here
    with patch("bot.cogs.performance_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = PerformanceCog(MagicMock(), mock_performance_service, mock_identity_service)
        await cog.stats.callback(cog, mock_interaction)

        mock_identity_service.get_user_by_discord_id.assert_called_once_with(str(12345))
        mock_performance_service.get_player_stats_from_cache.assert_not_called()
        assert "Not Linked" in mock_create_embed.call_args.kwargs.get("title", "")

@pytest.mark.asyncio
async def test_leaderboard_success(mock_performance_service, mock_identity_service, mock_interaction):
    mock_performance_service.get_arcade_leaderboard_from_cache.return_value = [
        {"rank": 1, "player_name": "Alice", "volforce": 15.0},
        {"rank": 2, "player_name": "Bob", "volforce": 14.5}
    ]
    with patch("bot.cogs.performance_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = PerformanceCog(MagicMock(), mock_performance_service, mock_identity_service)
        await cog.leaderboard.callback(cog, mock_interaction)

        mock_performance_service.get_arcade_leaderboard_from_cache.assert_called_once()
        mock_create_embed.assert_called_once()
        desc = mock_create_embed.call_args.kwargs.get("description", "")
        assert "Alice" in desc and "Bob" in desc

@pytest.mark.asyncio
async def test_leaderboard_empty(mock_performance_service, mock_identity_service, mock_interaction):
    mock_performance_service.get_arcade_leaderboard_from_cache.return_value = []
    with patch("bot.cogs.performance_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = PerformanceCog(MagicMock(), mock_performance_service, mock_identity_service)
        await cog.leaderboard.callback(cog, mock_interaction)

        desc = mock_create_embed.call_args.kwargs.get("description", "")
        assert "empty" in desc