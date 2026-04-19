
import asyncio
import logging
import os
import sys

# Add src to path
sys.path.append(os.path.abspath("src"))

from orchestrator import do_save_async
from core.exceptions import ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

async def run_dogfooding_pure():
    print("--- LogicHive Dogfooding (Pure Logic) Start ---")

    name = "api_payload_processor"
    description = "Pure logic to validate and process API responses using Pydantic. No I/O."

    code = """
from pydantic import BaseModel, Field
from typing import List, Optional

class UserData(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool = True

class ApiResponse(BaseModel):
    status: str
    users: List[UserData]
    next_page: Optional[str] = None

def process_api_payload(payload: dict) -> ApiResponse:
    \"\"\"
    Validates and transforms a raw API payload into a structured model.
    This is a 'Logic Atom' free from I/O side effects.
    \"\"\"
    response = ApiResponse(**payload)
    if response.status != "ok":
        raise ValueError(f"API Error: Status is {response.status}")
    return response
"""

    test_code = """
def test_processing():
    raw_data = {
        "status": "ok",
        "users": [
            {"id": 1, "username": "alice", "email": "alice@example.com"},
            {"id": 2, "username": "bob", "email": "bob@example.com", "is_active": False}
        ]
    }
    result = process_api_payload(raw_data)
    assert len(result.users) == 2
    assert result.users[0].username == "alice"
    assert result.users[1].is_active is False
    print("Pure Logic Verified!")

test_processing()
"""

    print(f"Registering asset: {name}...")
    try:
        success = await do_save_async(
            name=name,
            code=code,
            description=description,
            test_code=test_code,
            dependencies=["pydantic"],
            timeout=30
        )

        if success:
            print("\n✅ SUCCESS: 'api_payload_processor' is now a Verified Logic Unit (VLU)!")
        else:
            print("\n❌ REJECTED.")

    except ValidationError as e:
        print(f"\n⚠️ REJECTED with Details:\n{e}")
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR:\n{e}")

if __name__ == "__main__":
    asyncio.run(run_dogfooding_pure())
