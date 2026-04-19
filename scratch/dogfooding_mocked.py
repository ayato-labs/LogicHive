
import asyncio
import logging
import os
import sys

# Add src to path
sys.path.append(os.path.abspath("src"))

from orchestrator import do_save_async
from core.exceptions import ValidationError

# Configure logging to see the instrumentation
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

async def run_dogfooding_mocked():
    print("--- LogicHive Dogfooding (Mocked) Start ---")

    name = "resilient_data_fetcher_v2"
    description = "Asynchronous fetcher with retry logic. Demonstration of Strategy 1: Mocking I/O."

    code = """
import asyncio
import aiohttp
from pydantic import BaseModel
from typing import Dict, Any

class FetchResult(BaseModel):
    data: Dict[str, Any]

async def resilient_fetch_logic(url: str) -> FetchResult:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return FetchResult(data=data)
"""

    # Strategy 1: Use mock_imports and provide a test that relies on the mock
    test_code = """
import asyncio
from unittest.mock import AsyncMock, MagicMock
import aiohttp

async def test_mocked_fetch():
    # Setup the mock response
    mock_resp = AsyncMock()
    mock_resp.json.return_value = {"status": "success", "val": 100}
    mock_resp.__aenter__.return_value = mock_resp
    
    # Setup the mock session
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session.__aenter__.return_value = mock_session
    
    # Patch the ClientSession constructor
    aiohttp.ClientSession = MagicMock(return_value=mock_session)
    
    # Execute and verify
    result = await resilient_fetch_logic("http://anything.com")
    assert result.data["val"] == 100
    print("Logic Verified via Mock!")

if __name__ == "__main__":
    asyncio.run(test_mocked_fetch())
"""

    print(f"Registering asset: {name}...")
    try:
        success = await do_save_async(
            name=name,
            code=code,
            description=description,
            test_code=test_code,
            mock_imports=["aiohttp"], # Tell LogicHive to provide a LogicHiveSmartMock or ignore physical network
            dependencies=["pydantic", "aiohttp"],
            timeout=30
        )

        if success:
            print("\n✅ SUCCESS: Dogfooding completed. Asset registered.")
        else:
            print("\n❌ REJECTED: Logic Gate denied the asset.")

    except ValidationError as e:
        print(f"\n⚠️ REJECTED with Details:\n{e}")
        if e.details:
            import json
            print(json.dumps(e.details, indent=2))
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR:\n{e}")

if __name__ == "__main__":
    asyncio.run(run_dogfooding_mocked())
