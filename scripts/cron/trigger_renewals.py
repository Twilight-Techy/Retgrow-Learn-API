import asyncio
import logging
import os
import sys
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging for cron script
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

API_URL = os.getenv("API_URL", "http://localhost:8000")
CRON_SECRET = os.getenv("CRON_SECRET", "secret")

async def trigger_renewal():
    url = f"{API_URL}/cron/renew-subscriptions"
    headers = {
        "X-Cron-Secret": CRON_SECRET,
        "Content-Type": "application/json"
    }
    
    logger.info("Triggering renewal at: %s", url)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, timeout=60.0)
            
            if response.status_code == 200:
                logger.info("Renewal successful: %s", response.json())
            elif response.status_code == 403:
                logger.error("Forbidden: Invalid Cron Secret — %s", response.text)
            else:
                logger.error("Failed with status %s: %s", response.status_code, response.text)
                
        except Exception as e:
            logger.error("Error triggering renewal: %s", e)
            sys.exit(1)

async def check_api_health():
    url = f"{API_URL}/health"
    logger.info("Checking API health at: %s", url)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            if response.status_code == 200:
                logger.info("API is up and running")
                return True
            else:
                logger.warning("API returned status: %s", response.status_code)
                return False
        except Exception as e:
            logger.error("API is unreachable: %s", e)
            return False

async def main():
    if await check_api_health():
        await trigger_renewal()
    else:
        logger.error("Aborting renewal due to API unavailability")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
