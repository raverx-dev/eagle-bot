import functools
from typing import Callable, Any, Awaitable
from bot.utils.notification_service import NotificationService

class ScrapeErrorHandler:
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        self.failure_count = 0
        self.max_failures = 3
        self.system_is_down = False

    def handle_scrape_failures(self) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
        def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    result = await func(*args, **kwargs)
                except Exception as e:
                    self.failure_count += 1
                    if self.failure_count >= self.max_failures and not self.system_is_down:
                        self.system_is_down = True
                        await self.notification_service.send_admin_alert("System is DOWN: scraping failures have reached threshold.")
                    raise e
                else:
                    if self.system_is_down:
                        await self.notification_service.send_admin_alert("System has RECOVERED: scraping is working again.")
                        self.system_is_down = False
                    self.failure_count = 0
                    return result
            return wrapper
        return decorator