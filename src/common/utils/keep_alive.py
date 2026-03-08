import asyncio
import logging
import urllib.request
from urllib.error import URLError, HTTPError
from src.common.config import settings

logger = logging.getLogger(__name__)

async def keep_alive_task():
    """
    A background task that pings the application's health endpoint periodically.
    This prevents hosting providers (like Render free tier) from putting the service
    to sleep due to inactivity.
    """
    ping_interval_seconds = 14 * 60  # Ping every 14 minutes
    ping_url = f"{settings.API_URL.rstrip('/')}/health"

    logger.info(f"Keep-alive mechanism initialized. Pinging {ping_url} every {ping_interval_seconds} seconds.")

    while True:
        try:
            await asyncio.sleep(ping_interval_seconds)
            
            def ping():
                req = urllib.request.Request(ping_url, headers={'User-Agent': 'KeepAlive/1.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    return response.getcode()

            # Execute the synchronous network request in a dedicated thread
            status_code = await asyncio.to_thread(ping)
            logger.debug(f"Keep-alive ping successful: HTTP {status_code}")

        except HTTPError as e:
            logger.warning(f"Keep-alive ping failed with HTTP Error: {e.code}")
        except URLError as e:
            logger.warning(f"Keep-alive ping failed with URL Error: {e.reason}")
        except Exception as e:
            logger.error(f"Keep-alive ping encountered an unexpected error: {e}")
