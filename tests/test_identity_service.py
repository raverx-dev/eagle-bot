import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from bot.core.identity_service import IdentityService

@pytest.fixture
def mock_browser():
    browser = MagicMock()
    browser.scrape_leaderboard = AsyncMock()
    return browser

@pytest.fixture
def users_file_path():
    return "fake_users.json"

def test_link_user_new_user(users_file_path, mock_browser):
    # users.json is empty
    with patch("builtins.open", create=True) as mock_open, \
         patch("json.load", return_value={}), \
         patch.object(IdentityService, "_write_users") as mock_write:
        service = IdentityService(users_file_path, mock_browser)
        result = service.link_user("discord123", "1234-5678")
        # The normalized SDVX ID is "12345678"
        expected_data = {
            "12345678": {
                "sdvx_id": "12345678",
                "discord_id": "discord123"
            }
        }
        mock_write.assert_called_once_with(expected_data)
        assert result is True

def test_link_user_invalid_id(users_file_path, mock_browser):
    with patch("builtins.open", create=True), \
         patch("json.load", return_value={}), \
         patch.object(IdentityService, "_write_users") as mock_write:
        service = IdentityService(users_file_path, mock_browser)
        result = service.link_user("discord123", "abc")
        mock_write.assert_not_called()
        assert result is False

@pytest.mark.asyncio
async def test_update_player_cache_update_existing(users_file_path, mock_browser):
    # Existing user in users.json
    now_iso = datetime.now(timezone.utc).isoformat()
    users_data = {
        "12345678": {
            "sdvx_id": "12345678",
            "discord_id": "discord123",
            "player_name": "OldName",
            "volforce": 9000,
            "rank": 5,
            "last_updated": "old"
        }
    }
    scraped = [{
        "sdvx_id": "12345678",
        "player_name": "OldName",
        "volforce": 9500,
        "rank": 3
    }]
    with patch("builtins.open", create=True) as mock_open, \
         patch("json.load", return_value=users_data.copy()), \
         patch.object(IdentityService, "_write_users") as mock_write:
        mock_browser.scrape_leaderboard.return_value = scraped
        service = IdentityService(users_file_path, mock_browser)
        result = await service.update_player_cache()
        # The discord_id should be preserved, volforce/rank updated, last_updated set
        written = mock_write.call_args[0][0]
        assert written["12345678"]["discord_id"] == "discord123"
        assert written["12345678"]["volforce"] == 9500
        assert written["12345678"]["rank"] == 3
        assert "last_updated" in written["12345678"]
        assert result == []

@pytest.mark.asyncio
async def test_update_player_cache_discover_new(users_file_path, mock_browser):
    # users.json is empty, scrape returns one player
    scraped = [{
        "sdvx_id": "87654321",
        "player_name": "NewGuy",
        "volforce": 1234,
        "rank": 42
    }]
    with patch("builtins.open", create=True) as mock_open, \
         patch("json.load", return_value={}), \
         patch.object(IdentityService, "_write_users") as mock_write:
        mock_browser.scrape_leaderboard.return_value = scraped
        service = IdentityService(users_file_path, mock_browser)
        result = await service.update_player_cache()
        written = mock_write.call_args[0][0]
        assert "87654321" in written
        assert written["87654321"]["discord_id"] is None
        assert written["87654321"]["player_name"] == "NewGuy"
        assert result == ["NewGuy"]

@pytest.mark.asyncio
async def test_update_player_cache_scrape_fails(users_file_path, mock_browser):
    with patch("builtins.open", create=True), \
         patch("json.load", return_value={}), \
         patch.object(IdentityService, "_write_users") as mock_write:
        mock_browser.scrape_leaderboard.side_effect = RuntimeError("scrape failed")
        service = IdentityService(users_file_path, mock_browser)
        with pytest.raises(RuntimeError, match="scrape failed"):
            await service.update_player_cache()
        mock_write.assert_not_called()