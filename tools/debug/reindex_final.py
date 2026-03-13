import asyncio
import os
import sys
import logging

# Set up logging for the script
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.append(os.path.abspath("src"))

from storage.sqlite_api import sqlite_storage
from core.consolidation import LogicIntelligence
from core.config import GEMINI_API_KEY

SYSTEM_ORG_ID = "00000000-0000-0000-0000-000000000000"


async def reindex_all():
    logger.info("Starting Batch Re-indexing (Final Fix)...")

    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is missing.")
        return

    intel = LogicIntelligence(GEMINI_API_KEY)

    # Verify the provider/client
    provider = await intel._get_optimal_provider()
    logger.info(f"Using Provider: {provider} | Model: {intel.model_id}")

    orgs = await sqlite_storage.list_organizations()
    org_ids = [org["id"] for org in orgs]
    if SYSTEM_ORG_ID not in org_ids:
        org_ids.append(SYSTEM_ORG_ID)

    for org_id in org_ids:
        logger.info(f"Re-indexing functions for Organization: {org_id}")
        functions = await sqlite_storage.get_all_functions(org_id)

        for func in functions:
            name = func["name"]
            code = func["code"]
            logger.info(f"  -> Processing: {name}")

            try:
                # 1. Generate Metadata
                optimized = await intel.optimize_metadata(code, "", [])
                new_desc = optimized["description"]
                new_tags = optimized["tags"]

                if not new_desc:
                    logger.warning(
                        f"     !!! AI returned empty description for {name}."
                    )

                # 2. Construct RAG Document
                search_doc = intel.construct_search_document(
                    name, new_desc, new_tags, code
                )

                # 3. Generate Embedding
                new_emb = await intel.generate_embedding(search_doc)

                if not new_emb:
                    logger.warning(f"     !!! Failed to generate embedding for {name}.")
                    continue

                # 4. Update Database
                update_data = {
                    "name": name,
                    "code": code,
                    "description": new_desc,
                    "tags": new_tags,
                    "reliability_score": 1.0,
                    "embedding": new_emb,
                }

                success = await sqlite_storage.upsert_function(update_data, org_id)
                if success:
                    logger.info(f"     [Done] {name} re-indexed and DEFINITELY SAVED.")
                else:
                    logger.error(f"     [Fail] Failed to update {name}.")

            except Exception as e:
                logger.error(f"     [Error] {name}: {e}")

    logger.info("Batch Re-indexing (Final Fix) completed.")


if __name__ == "__main__":
    asyncio.run(reindex_all())
