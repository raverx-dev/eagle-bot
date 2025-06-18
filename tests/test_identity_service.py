# tests/test_identity_service.py
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from datetime import datetime, timezone 

from bot.eagle_browser import EagleBrowser
from bot.core.identity_service import IdentityService


@pytest.fixture
def mock_browser():
    """Provides a mock EagleBrowser with an async mock for scraping."""
    browser = MagicMock(spec=EagleBrowser)
    browser.scrape_leaderboard = AsyncMock()
    browser.scrape_player_profile = AsyncMock() # Ensure this is an AsyncMock
    return browser

@pytest.fixture
def users_file_path():
    """Provides a consistent fake file path for the user data file."""
    return "fake_users.json"


@pytest.mark.asyncio
async def test_link_user_new_user(users_file_path, mock_browser):
    """Tests that a new user can link their account successfully, with player_name from profile scrape."""
    with patch.object(IdentityService, '_read_users', return_value={}) as mock_read_users, \
         patch.object(IdentityService, '_write_users') as mock_write_users:
        
        service = IdentityService(users_file_path, mock_browser)
        # Mock profile scrape to return player_name (as per current _scrape_player_profile)
        mock_browser.scrape_player_profile.return_value = { 
            "player_name": "TestPlayerName", "recent_plays": [] # recent_plays included to match signature
        }
        result = await service.link_user(discord_id="discord123", sdvx_id="1234-5678") 

        assert result is True
        written_data = mock_write_users.call_args[0][0]
        assert "12345678" in written_data
        assert written_data["12345678"]["discord_id"] == "discord123"
        assert written_data["12345678"]["player_name"] == "TestPlayerName"
        # volforce and rank are NOT expected to be set by link_user at this stage
        assert "volforce" not in written_data["12345678"]
        assert "rank" not in written_data["12345678"]
        assert "last_updated" in written_data["12345678"]
        mock_browser.scrape_player_profile.assert_awaited_once_with("12345678")


@pytest.mark.asyncio
async def test_link_user_invalid_id(users_file_path, mock_browser):
    """Tests that linking fails with an invalid SDVX ID format."""
    with patch.object(IdentityService, '_write_users') as mock_write_users:
        service = IdentityService(users_file_path, mock_browser)
        result = await service.link_user(discord_id="discord123", sdvx_id="invalid-id") 
        
        assert result is False
        mock_write_users.assert_not_called()
        mock_browser.scrape_player_profile.assert_not_awaited() 


@pytest.mark.asyncio
async def test_update_player_cache_update_existing(users_file_path, mock_browser):
    """Test update_player_cache updates existing player data (name, volforce, rank) from leaderboard and enriches with recent_plays from profile."""
    initial_users = {
        "10000001": {"sdvx_id": "10000001", "discord_id": "d1", "player_name": "OldA", "volforce": 1.0, "rank": 5}
    }
    scraped_data = [{ # Leaderboard data - will be used to update core stats
        "sdvx_id": "10000001", "player_name": "LB_Player", "volforce": 3.0, "rank": 1 
    }]
    mock_browser.scrape_leaderboard.return_value = scraped_data
    
    # Profile scrape data - will be used to update player_name (if better) and recent_plays
    mock_browser.scrape_player_profile.return_value = {
        "player_name": "ProfileName", "recent_plays": [{"song_title": "TestSong", "is_new_record": False}] 
    }

    with patch.object(IdentityService, '_read_users', return_value=initial_users), \
         patch.object(IdentityService, '_write_users') as mock_write_users:
        
        service = IdentityService(users_file_path, mock_browser)
        new_players = await service.update_player_cache()
        
        assert new_players == [] # Expect no new players, as '10000001' was already in initial_users
        written_data = mock_write_users.call_args[0][0]
        # Assert data is updated from leaderboard for VF/Rank, and player_name from profile if provided
        assert written_data["10000001"]["volforce"] == 3.0 
        assert written_data["10000001"]["discord_id"] == "d1" 
        assert written_data["10000001"]["player_name"] == "ProfileName" # Profile name preferred if non-None
        assert written_data["10000001"]["rank"] == 1 
        assert "last_updated" in written_data["10000001"]
        assert written_data["10000001"]["recent_plays"] == [{"song_title": "TestSong", "is_new_record": False}] # Recent plays added
        mock_browser.scrape_leaderboard.assert_awaited_once() 
        mock_browser.scrape_player_profile.assert_awaited_once_with("10000001")


@pytest.mark.asyncio
async def test_update_player_cache_discover_new(users_file_path, mock_browser):
    """Tests that a truly new player from a leaderboard scrape is added and enriched with recent_plays."""
    scraped_data = [{ # Leaderboard data
        "sdvx_id": "87654321", "player_name": "NEWBIE_LB", "volforce": 1.0, "rank": 2
    }]
    mock_browser.scrape_leaderboard.return_value = scraped_data
    
    # Profile scrape data for the newly discovered player
    mock_browser.scrape_player_profile.return_value = {
        "player_name": "NEWBIE_Profile", "recent_plays": [{"song_title": "NewSong", "is_new_record": True}]
    }
    
    with patch.object(IdentityService, '_read_users', return_value={}), \
         patch.object(IdentityService, '_write_users') as mock_write_users:
        
        service = IdentityService(users_file_path, mock_browser)
        new_players = await service.update_player_cache()
        
        assert new_players == ["NEWBIE_LB"] # This list still reflects names from initial leaderboard discovery
        written_data = mock_write_users.call_args[0][0]
        assert "87654321" in written_data
        assert written_data["87654321"]["discord_id"] is None
        assert written_data["87654321"]["player_name"] == "NEWBIE_Profile" # Profile name preferred if set by mock
        assert written_data["87654321"]["volforce"] == 1.0 # From leaderboard
        assert written_data["87654321"]["rank"] == 2 # From leaderboard
        assert "last_updated" in written_data["87654321"]
        assert written_data["87654321"]["recent_plays"] == [{"song_title": "NewSong", "is_new_record": True}] # Recent plays added
        mock_browser.scrape_leaderboard.assert_awaited_once()
        mock_browser.scrape_player_profile.assert_awaited_once_with("87654321")


@pytest.mark.asyncio
async def test_update_player_cache_scrape_fails(users_file_path, mock_browser):
    """Tests that the service handles a failure from the web scraper."""
    mock_browser.scrape_leaderboard.side_effect = Exception("Leaderboard Scrape Failed")
    
    with patch.object(IdentityService, '_write_users') as mock_write_users:
        service = IdentityService(users_file_path, mock_browser)
        
        with pytest.raises(Exception, match="Leaderboard Scrape Failed"):
            await service.update_player_cache()
            
        mock_write_users.assert_not_called()
        mock_browser.scrape_player_profile.assert_not_awaited() 

@pytest.mark.asyncio
async def test_get_user_by_discord_id(users_file_path, mock_browser):
    """Tests finding a user by their Discord ID."""
    mock_data = {
        "11112222": {"discord_id": "discord1", "player_name": "Player One"},
        "33334444": {"discord_id": "discord2", "player_name": "Player Two"}
    }
    
    with patch.object(IdentityService, '_read_users', return_value=mock_data):
        service = IdentityService(users_file_path, mock_browser)
        
        found_user = await service.get_user_by_discord_id("discord2") 
        assert found_user is not None
        assert found_user["player_name"] == "Player Two"

        not_found_user = await service.get_user_by_discord_id("discord3") 
        assert not_found_user is None

@pytest.mark.asyncio
async def test_force_unlink_success(users_file_path, mock_browser):
    """Tests that an admin can forcibly unlink a user."""
    initial_users = {
        "11112222": {"discord_id": "discord1_to_unlink", "player_name": "Player One"}
    }
    with patch.object(IdentityService, '_read_users', return_value=initial_users), \
         patch.object(IdentityService, '_write_users') as mock_write_users:
        
        service = IdentityService(users_file_path, mock_browser)
        result = await service.force_unlink("discord1_to_unlink") 

        assert result is True
        written_data = mock_write_users.call_args[0][0]
        assert written_data["11112222"]["discord_id"] is None

@pytest.mark.asyncio
async def test_force_unlink_user_not_found(users_file_path, mock_browser):
    """Tests that force_unlink returns False if the user isn't linked."""
    with patch.object(IdentityService, '_read_users', return_value={}), \
         patch.object(IdentityService, '_write_users') as mock_write_users:

        service = IdentityService(users_file_path, mock_browser)
        result = await service.force_unlink("non_existent_discord_id") 

        assert result is False
        mock_write_users.assert_not_called()

@pytest.mark.asyncio
async def test_link_user_profile_enrichment_success(users_file_path, mock_browser):
    """Test link_user enriches the user profile with scraped data (name only) on success."""
    with patch.object(IdentityService, '_read_users', return_value={}), \
         patch.object(IdentityService, '_write_users') as mock_write_users:
        service = IdentityService(users_file_path, mock_browser)
        mock_browser.scrape_player_profile.return_value = {
            "player_name": "EnrichedName", "recent_plays": [] 
        }
        result = await service.link_user(discord_id="discordX", sdvx_id="8765-4321") 
        assert result is True
        written_data = mock_write_users.call_args[0][0]
        assert "87654321" in written_data
        assert written_data["87654321"]["player_name"] == "EnrichedName"
        assert "volforce" not in written_data["87654321"] 
        assert "rank" not in written_data["87654321"] 
        assert "last_updated" in written_data["87654321"]
        mock_browser.scrape_player_profile.assert_awaited_once_with("87654321")

@pytest.mark.asyncio
async def test_link_user_profile_enrichment_scrape_fails(users_file_path, mock_browser):
    """Test link_user still succeeds if scrape_player_profile fails (returns None/empty)."""
    with patch.object(IdentityService, '_read_users', return_value={}), \
         patch.object(IdentityService, '_write_users') as mock_write_users:
        service = IdentityService(users_file_path, mock_browser)
        mock_browser.scrape_player_profile.return_value = None
        result = await service.link_user(discord_id="discordY", sdvx_id="1111-2222") 
        assert result is True
        written_data = mock_write_users.call_args[0][0]
        assert "11112222" in written_data
        assert written_data["11112222"].get("player_name") is None
        assert "volforce" not in written_data["11112222"]
        assert "rank" not in written_data["11112222"]
        assert "last_updated" in written_data["11112222"]
        mock_browser.scrape_player_profile.assert_awaited_once_with("11112222")

@pytest.mark.asyncio
async def test_update_player_cache_enrich_existing_users(users_file_path, mock_browser):
    """Test update_player_cache updates existing users from leaderboard and gets recent_plays from profile."""
    initial_users = {
        "10000001": {"sdvx_id": "10000001", "discord_id": "d1", "player_name": "OldA", "volforce": 9.0, "rank": 5}
    }
    scraped_data = [ # Leaderboard data
        {"sdvx_id": "10000001", "player_name": "A_from_LB", "volforce": 10.0, "rank": 1},
        {"sdvx_id": "30000003", "player_name": "C_new", "volforce": 12.0, "rank": 3} 
    ]
    mock_browser.scrape_leaderboard.return_value = scraped_data
    
    def profile_scrape_side_effect(sdvx_id):
        if sdvx_id == "10000001":
            return {"player_name": "A_from_Profile", "recent_plays": [{"song_title": "ExistingSong", "is_new_record": False}]}
        elif sdvx_id == "30000003": 
            return {"player_name": "C_from_Profile", "recent_plays": [{"song_title": "NewSong", "is_new_record": True}]}
        return None 

    mock_browser.scrape_player_profile.side_effect = AsyncMock(side_effect=profile_scrape_side_effect)
    with patch.object(IdentityService, '_read_users', return_value=initial_users.copy()), \
         patch.object(IdentityService, '_write_users') as mock_write_users:
        service = IdentityService(users_file_path, mock_browser)
        new_players = await service.update_player_cache()
        
        assert new_players == ["C_new"] # Only 'C_new' is new from leaderboard
        
        written_data = mock_write_users.call_args[0][0]
        # Assert existing user updated from leaderboard for core stats, and profile for recent_plays/name
        assert written_data["10000001"]["player_name"] == "A_from_Profile" 
        assert written_data["10000001"]["volforce"] == 10.0 # From leaderboard
        assert written_data["10000001"]["rank"] == 1 # From leaderboard
        assert written_data["10000001"]["recent_plays"] == [{"song_title": "ExistingSong", "is_new_record": False}]
        
        # Assert new user populated from leaderboard and recent_plays from profile
        assert written_data["30000003"]["player_name"] == "C_from_Profile"
        assert written_data["30000003"]["volforce"] == 12.0
        assert written_data["30000003"]["rank"] == 3
        assert written_data["30000003"]["discord_id"] is None 
        assert written_data["30000003"]["recent_plays"] == [{"song_title": "NewSong", "is_new_record": True}]
        
        # Ensure scrape_player_profile was called for each relevant player
        expected_profile_scrape_calls = set(initial_users.keys()).union(set(p['sdvx_id'] for p in scraped_data if p.get('sdvx_id')))
        assert mock_browser.scrape_player_profile.await_count == len(expected_profile_scrape_calls)


@pytest.mark.asyncio
async def test_update_player_cache_enrich_existing_users_scrape_fails(users_file_path, mock_browser):
    """Test update_player_cache preserves old data if profile scrape fails for a user."""
    initial_users = {
        "10000001": {"sdvx_id": "10000001", "discord_id": "d1", "player_name": "OldA", "volforce": 9.0, "rank": 1, "recent_plays": [{"song_title": "OldSong", "is_new_record": False}]},
        "10000002": {"sdvx_id": "10000002", "discord_id": "d2", "player_name": "OldB", "volforce": 8.0, "rank": 2, "recent_plays": []}
    }
    scraped_data = [
        {"sdvx_id": "10000001", "player_name": "A_from_LB", "volforce": 10.0, "rank": 1},
        {"sdvx_id": "10000002", "player_name": "B_from_LB", "volforce": 11.0, "rank": 2}
    ]
    mock_browser.scrape_leaderboard.return_value = scraped_data
    
    def profile_scrape_side_effect(sdvx_id):
        if sdvx_id == "10000001":
            return {"player_name": "A_from_Profile", "recent_plays": [{"song_title": "UpdatedSong", "is_new_record": True}]}
        else:
            return None 
    mock_browser.scrape_player_profile.side_effect = AsyncMock(side_effect=profile_scrape_side_effect)
    with patch.object(IdentityService, '_read_users', return_value=initial_users.copy()), \
         patch.object(IdentityService, '_write_users') as mock_write_users:
        service = IdentityService(users_file_path, mock_browser)
        new_players = await service.update_player_cache()
        assert new_players == [] 
        written_data = mock_write_users.call_args[0][0]
        # User 1 should be updated from leaderboard (VF/Rank) and profile (name, recent_plays)
        assert written_data["10000001"]["player_name"] == "A_from_Profile"
        assert written_data["10000001"]["volforce"] == 10.0 
        assert written_data["10000001"]["rank"] == 1 
        assert written_data["10000001"]["recent_plays"] == [{"song_title": "UpdatedSong", "is_new_record": True}]

        # User 2's profile scrape failed, so only LB data should update core stats, recent_plays should be preserved as per logic
        assert written_data["10000002"]["player_name"] == "B_from_LB" 
        assert written_data["10000002"]["volforce"] == 11.0 
        assert written_data["10000002"]["rank"] == 2 
        assert written_data["10000002"]["recent_plays"] == initial_users["10000002"]["recent_plays"]
        assert mock_browser.scrape_player_profile.await_count == len(initial_users)