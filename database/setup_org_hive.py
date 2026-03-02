import asyncio
import logging
from typing import Optional
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load from LogicHive-Hub-Private/backend/.env typically
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_org_hive():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Missing Supabase credentials in environment.")
        return

    client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 1. Create Public Organization
    org_name = "Public Hive"
    org_key = "public_v1_key" # The default in config.py
    
    logger.info(f"Checking for organization '{org_name}'...")
    
    try:
        # Check if exists
        res = client.table("organizations").select("id").eq("name", org_name).execute()
        if res.data:
            org_id = res.data[0]["id"]
            logger.info(f"Organization already exists with ID: {org_id}")
        else:
            logger.info(f"Creating organization '{org_name}'...")
            res = client.table("organizations").insert({
                "name": org_name,
                "api_key_hash": org_key # In prod, this would be a real hash
            }).execute()
            org_id = res.data[0]["id"]
            logger.info(f"Created organization with ID: {org_id}")

        # 2. Update existing functions to link to this org
        logger.info("Linking orphan functions to 'Public Hive'...")
        res = client.table("logichive_functions").update({
            "organization_id": org_id
        }).is_("organization_id", "null").execute()
        
        count = len(res.data) if res.data else 0
        logger.info(f"Updated {count} functions.")
        
        logger.info("Setup complete!")
        logger.info(f"Your Organization Key: {org_key}")
        logger.info("Make sure LogicHive-Edge config has ORG_KEY = (this key)")

    except Exception as e:
        logger.error(f"Setup failed: {e}")

if __name__ == "__main__":
    asyncio.run(setup_org_hive())
