import os
import sys
import ast
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.append(os.path.abspath("src"))

from storage.sqlite_api import sqlite_storage
from core.consolidation import LogicIntelligence
from core.config import GEMINI_API_KEY, GEMINI_MODEL
from core.hash_utils import calculate_code_hash

SYSTEM_ORG_ID = "00000000-0000-0000-0000-000000000000"


def extract_functions_from_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    functions = []
    # Get all lines once
    with open(file_path, "r", encoding="utf-8") as f:
        code_lines = f.readlines()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith("__"):
                continue

            # Extract source code for this specific function
            start = node.lineno - 1
            end = node.end_lineno
            func_code = "".join(code_lines[start:end])

            functions.append(
                {
                    "name": node.name,
                    "code": func_code,
                    "description": ast.get_docstring(node) or "",
                }
            )
    return functions


async def main():
    logger.info(
        f"Scanning src/core and src/storage for functions using model {GEMINI_MODEL}..."
    )
    target_dirs = ["src/core", "src/storage"]
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY missing.")
        return

    intel = LogicIntelligence(GEMINI_API_KEY)

    total_processed = 0
    total_skipped = 0
    total_updated = 0

    for d in target_dirs:
        abs_d = os.path.abspath(d)
        if not os.path.exists(abs_d):
            continue

        for root, _, files in os.walk(abs_d):
            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    path = os.path.join(root, file)
                    logger.info(f"Processing {path}...")
                    try:
                        funcs = extract_functions_from_file(path)
                        for f_data in funcs:
                            total_processed += 1
                            name = f_data["name"]
                            code = f_data["code"]

                            # 1. Calculate current hash
                            current_hash = calculate_code_hash(code)

                            # 2. Check existing in DB
                            existing = await sqlite_storage.get_function_by_name(
                                name, SYSTEM_ORG_ID
                            )
                            if existing and existing.get("code_hash") == current_hash:
                                logger.info(f"     [Skip] {name} (Unchanged)")
                                total_skipped += 1
                                continue

                            logger.info(f"  -> Generating technical spec for {name}...")
                            # 3. Generate rich metadata
                            optimized = await intel.optimize_metadata(
                                code, f_data["description"]
                            )

                            desc = optimized["description"]
                            tags = optimized["tags"]

                            # 4. Build RAG doc for embedding
                            search_doc = intel.construct_search_document(
                                name, desc, tags, code
                            )

                            # 5. Generate embedding
                            emb = await intel.generate_embedding(search_doc)

                            if not emb:
                                logger.warning(
                                    f"     [Skip] Failed to generate embedding for {name}"
                                )
                                continue

                            # 6. Upsert to DB
                            final_data = {
                                "name": name,
                                "code": code,
                                "description": desc,
                                "tags": tags,
                                "reliability_score": 1.0,
                                "embedding": emb,
                                "code_hash": current_hash,  # Store the hash!
                            }

                            success = await sqlite_storage.upsert_function(
                                final_data, SYSTEM_ORG_ID
                            )
                            if success:
                                logger.info(f"     [Saved] {name}")
                                total_updated += 1
                            else:
                                logger.error(f"     [Error] Failed to save {name}")
                    except Exception as e:
                        logger.error(f"Error processing {path}: {e}")

    logger.info(
        f"Finished! Processed: {total_processed}, Updated: {total_updated}, Skipped: {total_skipped}"
    )


if __name__ == "__main__":
    asyncio.run(main())
