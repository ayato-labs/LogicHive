import asyncio
import os
import json
import logging
from orchestrator import do_save_async

# Configure logging to see the instrumentation
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

async def run_dogfooding():
    print("--- LogicHive Dogfooding Start ---")
    
    name = "resilient_data_fetcher"
    description = "Advanced asynchronous fetcher with pydantic validation and exponential backoff."
    
    code = """
import asyncio
import aiohttp
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Optional

class FetchConfig(BaseModel):
    url: HttpUrl
    retries: int = 3
    timeout: float = 5.0

async def resilient_fetch(url: str, config_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    \"\"\"
    Fetches data from a URL with retry logic and validation.
    \"\"\"
    cfg = FetchConfig(url=url, **(config_dict or {}))
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(cfg.retries):
            try:
                async with session.get(str(cfg.url), timeout=cfg.timeout) as response:
                    if response.status == 200:
                        return await response.json()
                    response.raise_for_status()
            except Exception as e:
                if attempt == cfg.retries - 1:
                    raise
                await asyncio.sleep(0.1 * (2 ** attempt)) # Fast backoff for test
    return {}
"""

    test_code = """
import asyncio
from unittest.mock import MagicMock, patch

async def test_fetch():
    # Use a mock for actual network I/O in the sandbox test
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = MagicMock(return_value={"status": "ok", "data": 123})
        mock_response.__aenter__.return_value = mock_response
        mock_get.return_value = mock_response
        
        result = await resilient_fetch("https://api.example.com/data")
        assert result["status"] == "ok"
        assert result["data"] == 123
        print("Test passed internally!")

if __name__ == "__main__":
    asyncio.run(test_fetch())
"""

    # We use a custom timeout to verify the new feature
    print(f"Registering asset: {name}...")
    try:
        success = await do_save_async(
            name=name,
            code=code,
            description=description,
            test_code=test_code,
            dependencies=["pydantic", "aiohttp"],
            timeout=45 # Custom timeout test
        )
        
        if success:
            print("\n--- Dogfooding SUCCESS ---")
            print(f"Asset '{name}' approved and registered.")
            # We don't have direct access to the duration here in return bool, 
            # but we can see it in the console logs if logging is ON.
        else:
            print("\n--- Dogfooding REJECTED ---")
            
    except Exception as e:
        print(f"\n--- Dogfooding ERROR ---\n{e}")

if __name__ == "__main__":
    asyncio.run(run_dogfooding())
