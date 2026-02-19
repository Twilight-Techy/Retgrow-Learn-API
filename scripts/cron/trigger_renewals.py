import asyncio
import os
import sys
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")
CRON_SECRET = os.getenv("CRON_SECRET", "secret")

async def trigger_renewal():
    url = f"{API_URL}/cron/renew-subscriptions"
    headers = {
        "X-Cron-Secret": CRON_SECRET,
        "Content-Type": "application/json"
    }
    
    print(f"Triggering renewal at: {url}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, timeout=60.0)
            
            if response.status_code == 200:
                print("✅ Success!")
                print(f"Response: {response.json()}")
            elif response.status_code == 403:
                print("❌ Forbidden: Invalid Cron Secret")
                print(f"Response: {response.text}")
            else:
                print(f"❌ Failed with status: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            sys.exit(1)

async def check_api_health():
    url = f"{API_URL}/health"
    print(f"Checking API health at: {url}...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            if response.status_code == 200:
                print("✅ API is up and running.")
                return True
            else:
                print(f"⚠️ API returned status: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API is unreachable: {str(e)}")
            return False

async def main():
    if await check_api_health():
        await trigger_renewal()
    else:
        print("Aborting renewal due to API unavailability.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
