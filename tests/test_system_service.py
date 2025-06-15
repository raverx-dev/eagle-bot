import pytest
import json
from unittest.mock import patch, mock_open
from datetime import datetime
import pytz

from bot.core.system_service import SystemService

MOCK_SCHEDULE = {
    "tuesday": {"open": "10:00", "close": "20:00"},
    "wednesday": {"closed": True},
    "friday": {"open": "22:00", "close": "02:00"}
}

@pytest.fixture
def mock_schedule_file():
    """Mocks the open() call to return the mock schedule."""
    with patch("builtins.open", mock_open(read_data=json.dumps(MOCK_SCHEDULE))) as mock_file:
        yield mock_file

@pytest.fixture
def service(mock_schedule_file):
    """Provides a SystemService instance initialized with the mocked schedule."""
    return SystemService("fake_path.json")


@pytest.mark.parametrize("scenario_time, expected", [
    # Tuesday is a normal day (10:00 - 20:00)
    ("2023-10-10 15:00:00", True),  # In hours
    ("2023-10-10 09:59:59", False), # Just before open
    ("2023-10-10 20:00:00", False), # Exactly at close
    
    # Wednesday is a closed day
    ("2023-10-11 14:00:00", False), # Any time on a closed day
    
    # Friday is an overnight day (22:00 - 02:00)
    ("2023-10-13 21:59:59", False), # Just before open
    ("2023-10-13 22:00:00", True),  # Exactly at open
    ("2023-10-14 00:00:00", True),  # Midnight, now Saturday
    ("2023-10-14 01:59:59", True),  # Just before close
    ("2023-10-14 02:00:00", False)  # Exactly at close
])
def test_is_within_arcade_hours(service, scenario_time, expected):
    # Create a timezone-aware datetime object for the test case
    mock_time = datetime.fromisoformat(scenario_time).replace(tzinfo=pytz.utc)
    
    # Patch the _get_now method to control the "current" time
    with patch.object(service, '_get_now', return_value=mock_time):
        assert service.is_within_arcade_hours() is expected


def test_init_file_not_found():
    with patch("builtins.open", side_effect=FileNotFoundError):
        service = SystemService("non_existent_path.json")
        assert service.schedule == {}