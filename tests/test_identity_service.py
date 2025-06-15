import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Assuming EagleBrowser is importable for type hinting, even if not implemented
from bot.eagle_browser import EagleBrowser
from bot.core.identity_service import IdentityService


@pytest.fixture
def mock_browser():
    """Provides a mock EagleBrowser with an async mock for scraping."""
    browser = MagicMock(spec=EagleBrowser)
    browser.scrape_leaderboard = AsyncMock()
    return browser

@pytest.fixture
def users_file_path():
    """Provides a consistent fake file path for the user data file."""
    return "fake_users.json"


def test_link_user_new_user(users_file_path, mock_browser):
    """Tests that a new user can link their account successfully."""
    with patch.object(IdentityService, '_read_users', return_value={}), \
         patch.object(IdentityService, '_write_users') as mock_write:
        
        service = IdentityService(users_file_path, mock_browser)
        result = service.link_user(discord_id="discord123", sdvx_id="1234-5678")

        assert result is True
        written_data = mock_write.call_args[0][0]
        assert "12345678" in written_data
        assert written_data["12345678"]["discord_id"] == "discord123"

def test_link_user_invalid_id(users_file_path, mock_browser):
    """Tests that linking fails with an invalid SDVX ID format."""
    with patch.object(IdentityService, '_write_users') as mock_write:
        service = IdentityService(users_file_path, mock_browser)
        result = service.link_user(discord_id="discord123", sdvx_id="invalid-id")
        
        assert result is False
        mock_write.assert_not_called()

@pytest.mark.asyncio
async def test_update_player_cache_update_existing(users_file_path, mock_browser):
    """Tests that an existing player's stats are updated from a scrape."""
    initial_users = {
        "12345678": {"sdvx_id": "12345678", "discord_id": "discord123", "volforce": 1.0}
    }
    scraped_data = [{
        "sdvx_id": "12345678", "player_name": "PLAYER", "volforce": 2.0, "rank": 1
    }]
    mock_browser.scrape_leaderboard.return_value = scraped_data

    with patch.object(IdentityService, '_read_users', return_value=initial_users), \
         patch.object(IdentityService, '_write_users') as mock_write:
        
        service = IdentityService(users_file_path, mock_browser)
        new_players = await service.update_player_cache()
        
        assert new_players == []
        written_data = mock_write.call_args[0][0]
        assert written_data["12345678"]["volforce"] == 2.0
        assert written_data["12345678"]["discord_id"] == "discord123"

@pytest.mark.asyncio
async def test_update_player_cache_discover_new(users_file_path, mock_browser):
    """Tests that a new player from a scrape is added to the cache correctly."""
    scraped_data = [{
        "sdvx_id": "87654321", "player_name": "NEWBIE", "volforce": 1.0, "rank": 2
    }]
    mock_browser.scrape_leaderboard.return_value = scraped_data
    
    with patch.object(IdentityService, '_read_users', return_value={}), \
         patch.object(IdentityService, '_write_users') as mock_write:
        
        service = IdentityService(users_file_path, mock_browser)
        new_players = await service.update_player_cache()
        
        assert new_players == ["NEWBIE"]
        written_data = mock_write.call_args[0][0]
        assert "87654321" in written_data
        assert written_data["87654321"]["discord_id"] is None

@pytest.mark.asyncio
async def test_update_player_cache_scrape_fails(users_file_path, mock_browser):
    """Tests that the service handles a failure from the web scraper."""
    mock_browser.scrape_leaderboard.side_effect = Exception("Scrape Failed")
    
    with patch.object(IdentityService, '_write_users') as mock_write:
        service = IdentityService(users_file_path, mock_browser)
        
        with pytest.raises(Exception, match="Scrape Failed"):
            await service.update_player_cache()
            
        mock_write.assert_not_called()

def test_get_user_by_discord_id(users_file_path, mock_browser):
    """Tests finding a user by their Discord ID."""
    mock_data = {
        "11112222": {"discord_id": "discord1", "player_name": "Player One"},
        "33334444": {"discord_id": "discord2", "player_name": "Player Two"}
    }
    
    with patch.object(IdentityService, '_read_users', return_value=mock_data):
        service = IdentityService(users_file_path, mock_browser)
        
        found_user = service.get_user_by_discord_id("discord2")
        assert found_user is not None
        assert found_user["player_name"] == "Player Two"

        not_found_user = service.get_user_by_discord_id("discord3")
        assert not_found_user is None

# --- New Tests for force_unlink ---

def test_force_unlink_success(users_file_path, mock_browser):
    """Tests that an admin can forcibly unlink a user."""
    initial_users = {
        "11112222": {"discord_id": "discord1_to_unlink", "player_name": "Player One"}
    }
    with patch.object(IdentityService, '_read_users', return_value=initial_users), \
         patch.object(IdentityService, '_write_users') as mock_write:
        
        service = IdentityService(users_file_path, mock_browser)
        result = service.force_unlink("discord1_to_unlink")

        assert result is True
        written_data = mock_write.call_args[0][0]
        assert written_data["11112222"]["discord_id"] is None

def test_force_unlink_user_not_found(users_file_path, mock_browser):
    """Tests that force_unlink returns False if the user isn't linked."""
    with patch.object(IdentityService, '_read_users', return_value={}), \
         patch.object(IdentityService, '_write_users') as mock_write:

        service = IdentityService(users_file_path, mock_browser)
        result = service.force_unlink("non_existent_discord_id")

        assert result is False
        mock_write.assert_not_called()