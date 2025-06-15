import pytest
from unittest.mock import patch
from bot.core.performance_service import PerformanceService

@pytest.fixture
def service():
    return PerformanceService("fake_users.json")

def test_get_player_stats_from_cache_found(service):
    mock_users = {"1234": {"sdvx_id": "1234", "name": "Alice"}}
    with patch.object(service, "_read_users", return_value=mock_users):
        result = service.get_player_stats_from_cache("1234")
        assert result == {"sdvx_id": "1234", "name": "Alice"}

def test_get_player_stats_from_cache_not_found(service):
    mock_users = {"5678": {"sdvx_id": "5678", "name": "Bob"}}
    with patch.object(service, "_read_users", return_value=mock_users):
        result = service.get_player_stats_from_cache("9999")
        assert result is None

def test_get_arcade_leaderboard_from_cache(service):
    mock_users = {
        str(i): {"sdvx_id": str(i), "rank": i, "name": f"User{i}"} for i in range(1, 13)
    }
    mock_users["no_rank"] = {"sdvx_id": "no_rank", "name": "NoRank"}  # No 'rank' key
    with patch.object(service, "_read_users", return_value=mock_users):
        result = service.get_arcade_leaderboard_from_cache()
        assert len(result) == 10
        assert all("rank" in user for user in result)
        assert result == sorted(result, key=lambda u: u["rank"])
        assert all(user["sdvx_id"] != "no_rank" for user in result)

def test_analyze_new_scores_for_records(service):
    plays = [
        {"score": 100, "is_new_record": True},
        {"score": 90, "is_new_record": False},
        {"score": 80},
        {"score": 110, "is_new_record": True}
    ]
    result = service.analyze_new_scores_for_records(plays)
    assert result == [
        {"score": 100, "is_new_record": True},
        {"score": 110, "is_new_record": True}
    ]

@pytest.mark.parametrize("old_vf,new_vf,expected", [
    (14.9, 15.1, "Scarlet I"),
    (15.1, 15.2, None),
    (15.9, 16.6, "Coral III"),
    (18.9, 19.0, "Crimson I"),
])
def test_check_for_vf_milestone(service, old_vf, new_vf, expected):
    assert service.check_for_vf_milestone(old_vf, new_vf) == expected
