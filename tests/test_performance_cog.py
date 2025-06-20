# tests/test_performance_cog.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from bot.cogs.performance_cog import PerformanceCog

@pytest.fixture
def mock_performance_service():
    svc = MagicMock()
    svc.get_arcade_leaderboard_from_cache = MagicMock()
    return svc

@pytest.fixture
def mock_identity_service():
    svc = MagicMock()
    svc.get_user_by_discord_id = AsyncMock()
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
    # FIX: The test now reflects the new data structure and embed format.
    mock_user_profile = {
        "sdvx_id": "9999-8888",
        "player_name": "TestUser",
        "volforce": 15.123,
        "skill_level": "Lv.10",
        "total_plays": 500,
        "recent_plays": [{"song_title": "Song A", "chart": "EXH 18", "grade": "S", "score": "9900123", "timestamp": "1 day ago"}]
    }
    mock_identity_service.get_user_by_discord_id.return_value = mock_user_profile

    with patch("bot.cogs.performance_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = PerformanceCog(MagicMock(), mock_performance_service, mock_identity_service)
        await cog.stats.callback(cog, mock_interaction)

        mock_identity_service.get_user_by_discord_id.assert_called_once_with(str(12345))
        mock_create_embed.assert_called_once()
        
        # Verify the new title and fields
        kwargs = mock_create_embed.call_args.kwargs
        assert "📊 Stats for TestUser (9999-8888)" in kwargs.get("title")
        assert len(kwargs.get("fields")) == 4
        assert kwargs.get("fields")[0]["name"] == "Volforce"
        assert "Song A" in kwargs.get("fields")[3]["value"]

@pytest.mark.asyncio
async def test_stats_user_not_linked(mock_performance_service, mock_identity_service, mock_interaction):
    mock_identity_service.get_user_by_discord_id.return_value = None
    with patch("bot.cogs.performance_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = PerformanceCog(MagicMock(), mock_performance_service, mock_identity_service)
        await cog.stats.callback(cog, mock_interaction)
        assert "Not Linked" in mock_create_embed.call_args.kwargs.get("title", "")

@pytest.mark.asyncio
async def test_leaderboard_success(mock_performance_service, mock_identity_service, mock_interaction):
    mock_performance_service.get_arcade_leaderboard_from_cache.return_value = [
        {"rank": 1, "player_name": "Alice", "volforce": 15.0},
    ]
    with patch("bot.cogs.performance_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = PerformanceCog(MagicMock(), mock_performance_service, mock_identity_service)
        await cog.leaderboard.callback(cog, mock_interaction)
        assert "Alice" in mock_create_embed.call_args.kwargs.get("description", "")
        # Check for new title
        assert "🏆 Arcade 94 - SDVX Top 10" in mock_create_embed.call_args.kwargs.get("title")

@pytest.mark.asyncio
async def test_leaderboard_empty(mock_performance_service, mock_identity_service, mock_interaction):
    mock_performance_service.get_arcade_leaderboard_from_cache.return_value = []
    with patch("bot.cogs.performance_cog.create_embed", return_value="embed") as mock_create_embed:
        cog = PerformanceCog(MagicMock(), mock_performance_service, mock_identity_service)
        await cog.leaderboard.callback(cog, mock_interaction)
        assert "empty" in mock_create_embed.call_args.kwargs.get("description", "")