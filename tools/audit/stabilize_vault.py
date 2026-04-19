import asyncio
import logging
import sys
from pathlib import Path

# Add src to sys.path to allow importing core components
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from core.evaluation.plugins.runtime import RuntimeEvaluator
from storage.sqlite_api import sqlite_storage

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Stabilizer")


async def stabilize_vault(dry_run: bool = True, project: str = "default"):
    print("\n" + "=" * 60)
    print(f"LOGICHIVE VAULT STABILIZATION TOOL {'(DRY RUN)' if dry_run else ''}")
    print("=" * 60)

    # 1. Fetch functions to audit
    all_functions = await sqlite_storage.get_all_functions()
    drafts = [
        f
        for f in all_functions
        if f.get("project") == project and "[AI-DRAFT]" in (f.get("description") or "")
    ]

    if not drafts:
        logger.info(f"No AI-DRAFT assets found in project '{project}'.")
        return

    logger.info(f"Found {len(drafts)} drafts to stabilize.")

    evaluator = RuntimeEvaluator()
    promoted_count = 0
    failed_count = 0
    skipped_count = 0

    for func in drafts:
        name = func["name"]
        code = func["code"]
        test_code = func.get("test_code", "")
        dependencies = func.get("dependencies", [])
        lang = func.get("language", "python")

        if not test_code:
            logger.warning(f"  [-] {name}: Skipping (No test code provided)")
            skipped_count += 1
            continue

        logger.info(f"  [*] {name}: Verifying in sandbox...")

        try:
            # We use the RuntimeEvaluator which uses the EphemeralPythonExecutor (Sandbox)
            result = await evaluator.evaluate(
                code=code, language=lang, test_code=test_code, dependencies=dependencies
            )

            if result.score == 100.0:
                logger.info(f"  [+] {name}: PASSED")
                promoted_count += 1

                if not dry_run:
                    # Update DB
                    new_description = func["description"].replace("[AI-DRAFT]", "[VERIFIED]")
                    # Handle case where it was already [VERIFIED] but score was low (unlikely here)
                    if "[VERIFIED]" not in new_description:
                        new_description = f"[VERIFIED] {new_description}"

                    # Prepare update data
                    # We reuse upsert logic or do a targeted update
                    # For simplicity in this tool, we use upsert which handles FAISS too
                    update_data = func.copy()
                    update_data["description"] = new_description
                    update_data["reliability_score"] = 1.0

                    await sqlite_storage.upsert_function(update_data)
                    logger.info("      -> Promoted in database.")
            else:
                logger.error(f"  [x] {name}: FAILED - {result.reason}")
                failed_count += 1

                if not dry_run:
                    # Append error to description and lower reliability score
                    error_msg = f"\n(Validation Failed: {result.reason})"
                    if error_msg not in func["description"]:
                        update_data = func.copy()
                        update_data["description"] += error_msg
                        # Pennalize the score: Runtime failed -> 0, AI/Static might still be high but overall it's untrustworthy
                        update_data["reliability_score"] = float(result.score) / 100.0
                        await sqlite_storage.upsert_function(update_data)
                        logger.info("      -> Flagged and penalized in database.")

        except Exception as e:
            logger.error(f"  [!] {name}: Unexpected error during verification: {e}")
            failed_count += 1

    print("\n" + "-" * 40)
    print(f"Audit Summary for '{project}':")
    print(f"  Promoted: {promoted_count}")
    print(f"  Failed:   {failed_count}")
    print(f"  Skipped:  {skipped_count}")
    print("-" * 40 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LogicHive Vault Stabilizer")
    parser.add_argument(
        "--run", action="store_true", help="Actually update the database (default is dry-run)"
    )
    parser.add_argument("--project", default="default", help="Project namespace to audit")

    args = parser.parse_args()

    # Run the async loop
    asyncio.run(stabilize_vault(dry_run=not args.run, project=args.project))
