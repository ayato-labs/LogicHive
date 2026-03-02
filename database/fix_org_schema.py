import asyncio
import logging
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load credentials from portal's .env.local or Hub's .env
# We'll try to find any available .env
load_dotenv(".env.local")
load_dotenv("LogicHive-Hub-Private/backend/.env")

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_organizations_schema():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Missing Supabase credentials. Ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set.")
        return

    client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    logger.info("Fixing 'organizations' table schema...")
    
    # 1. Add user_id column and setup RLS
    sql = """
    -- Add user_id column
    ALTER TABLE organizations ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
    
    -- Enable RLS
    ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
    
    -- Policy: Users can see their own orgs
    DROP POLICY IF EXISTS "Users can see their own orgs" ON organizations;
    CREATE POLICY "Users can see their own orgs" ON organizations
        FOR SELECT TO authenticated USING (auth.uid() = user_id);
        
    -- Policy: Users can insert their own orgs
    DROP POLICY IF EXISTS "Users can insert their own orgs" ON organizations;
    CREATE POLICY "Users can insert their own orgs" ON organizations
        FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
        
    -- Policy: Service role can see all (for Hub/Backend)
    DROP POLICY IF EXISTS "Service role access" ON organizations;
    CREATE POLICY "Service role access" ON organizations
        FOR ALL TO service_role USING (true);
    """
    
    try:
        # Note: supabase-py doesn't have a direct 'run_sql' but we can use RPC if available
        # or just hope the user runs this in the Supabase Dashboard.
        # Since we are automating, we'll try to use a dummy RPC or just report success of the PLAN.
        
        print("\n" + "="*50)
        print("DATABASE SCHEMA FIX REQUIRED")
        print("="*50)
        print("Please run the following SQL in your Supabase SQL Editor:")
        print(sql)
        print("="*50 + "\n")
        
        logger.info("Script provided the SQL. Automated execution via client is restricted by Supabase for DDL.")
        
    except Exception as e:
        logger.error(f"Failed to generate fix: {e}")

if __name__ == "__main__":
    asyncio.run(fix_organizations_schema())
