import pytest
from unittest.mock import AsyncMock, MagicMock

from bot.utils.error_handler import ScrapeErrorHandler

# A dummy exception for testing
class ScrapeTestError(Exception):
    pass

@pytest.fixture
def mock_notification_service():
    """Provides a mock NotificationService with an async mock for sending alerts."""
    service = MagicMock(spec=['send_admin_alert'])
    service.send_admin_alert = AsyncMock()
    return service

@pytest.fixture
def handler(mock_notification_service):
    """Provides a fresh instance of the ScrapeErrorHandler for each test."""
    return ScrapeErrorHandler(mock_notification_service)

@pytest.fixture
def mock_scrape_func():
    """Provides a basic async mock function to be decorated."""
    return AsyncMock(return_value="ok")


@pytest.mark.asyncio
async def test_success_on_first_try(handler, mock_notification_service, mock_scrape_func):
    decorated_func = handler.handle_scrape_failures()(mock_scrape_func)
    
    result = await decorated_func()
    
    assert result == "ok"
    assert handler.failure_count == 0
    mock_notification_service.send_admin_alert.assert_not_awaited()

@pytest.mark.asyncio
async def test_single_failure(handler, mock_notification_service, mock_scrape_func):
    mock_scrape_func.side_effect = ScrapeTestError("fail")
    decorated_func = handler.handle_scrape_failures()(mock_scrape_func)
    
    with pytest.raises(ScrapeTestError):
        await decorated_func()
        
    assert handler.failure_count == 1
    mock_notification_service.send_admin_alert.assert_not_awaited()

@pytest.mark.asyncio
async def test_reaching_failure_threshold(handler, mock_notification_service, mock_scrape_func):
    mock_scrape_func.side_effect = ScrapeTestError("fail")
    decorated_func = handler.handle_scrape_failures()(mock_scrape_func)
    
    # First 2 failures should not alert
    with pytest.raises(ScrapeTestError): await decorated_func()
    with pytest.raises(ScrapeTestError): await decorated_func()
    mock_notification_service.send_admin_alert.assert_not_awaited()
    assert handler.system_is_down is False
    
    # 3rd failure should alert
    with pytest.raises(ScrapeTestError):
        await decorated_func()
        
    mock_notification_service.send_admin_alert.assert_awaited_once()
    assert "System is DOWN" in mock_notification_service.send_admin_alert.call_args[0][0]
    assert handler.system_is_down is True

@pytest.mark.asyncio
async def test_alert_not_sent_when_already_down(handler, mock_notification_service, mock_scrape_func):
    mock_scrape_func.side_effect = ScrapeTestError("fail")
    decorated_func = handler.handle_scrape_failures()(mock_scrape_func)

    # Fail 3 times to trigger the alert
    for _ in range(3):
        with pytest.raises(ScrapeTestError): await decorated_func()
    
    mock_notification_service.send_admin_alert.assert_awaited_once() # Alert sent once
    
    # Fail a 4th time
    with pytest.raises(ScrapeTestError):
        await decorated_func()
        
    # Assert alert was not sent again
    mock_notification_service.send_admin_alert.assert_awaited_once()
    assert handler.failure_count == 4

@pytest.mark.asyncio
async def test_system_recovery(handler, mock_notification_service, mock_scrape_func):
    decorated_func = handler.handle_scrape_failures()(mock_scrape_func)

    # Fail 3 times
    mock_scrape_func.side_effect = ScrapeTestError("fail")
    for _ in range(3):
        with pytest.raises(ScrapeTestError): await decorated_func()
    
    # Confirm system is down
    assert handler.system_is_down is True
    mock_notification_service.send_admin_alert.assert_awaited_once_with(
        "System is DOWN: scraping failures have reached threshold."
    )
    
    # Now succeed
    mock_scrape_func.side_effect = None # Reset side effect to allow success
    mock_scrape_func.return_value = "ok"
    await decorated_func()

    # Check for recovery alert
    assert mock_notification_service.send_admin_alert.call_count == 2
    mock_notification_service.send_admin_alert.assert_any_await(
        "System has RECOVERED: scraping is working again."
    )
    assert handler.system_is_down is False
    assert handler.failure_count == 0

@pytest.mark.asyncio
async def test_failure_count_reset(handler, mock_notification_service, mock_scrape_func):
    decorated_func = handler.handle_scrape_failures()(mock_scrape_func)

    # Fail twice
    mock_scrape_func.side_effect = ScrapeTestError("fail")
    with pytest.raises(ScrapeTestError): await decorated_func()
    with pytest.raises(ScrapeTestError): await decorated_func()
    
    assert handler.failure_count == 2
    mock_notification_service.send_admin_alert.assert_not_awaited()
    
    # Succeed once
    mock_scrape_func.side_effect = None
    await decorated_func()
    
    assert handler.failure_count == 0
    
    # Fail again
    mock_scrape_func.side_effect = ScrapeTestError("fail")
    with pytest.raises(ScrapeTestError):
        await decorated_func()
        
    assert handler.failure_count == 1
    mock_notification_service.send_admin_alert.assert_not_awaited()