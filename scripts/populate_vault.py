import asyncio
import sys
import ast
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from orchestrator import do_save_async


def extract_functions_from_file(file_path):
    """Parses a file and returns a list of (function_name, code) tuples."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    tree = ast.parse(content)
    functions = []
    lines = content.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Extract the raw code for the function
            start = node.lineno - 1
            end = node.end_lineno
            func_code = "\n".join(lines[start:end])
            functions.append((node.name, func_code))
        elif isinstance(node, ast.ClassDef):
            # Also extract class methods
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    start = item.lineno - 1
                    end = item.end_lineno
                    func_code = "\n".join(lines[start:end])
                    functions.append((f"{node.name}.{item.name}", func_code))

    return functions


async def populate():
    print("=== LogicHive Vault Comprehensive Population ===")

    target_files = [
        "src/orchestrator.py",
        "src/core/consolidation.py",
        "src/core/hash_utils.py",
        "src/storage/sqlite_api.py",
        "src/storage/vector_store.py",
        "src/storage/init_db.py",
        "ci_cd/cd_github.py",
        "ci_cd/build_exe.py",
    ]

    project_root = Path(__file__).parent.parent

    all_extracted = []
    for rel_path in target_files:
        abs_path = project_root / rel_path
        if abs_path.exists():
            print(f"Extracting from: {rel_path}...")
            funcs = extract_functions_from_file(abs_path)
            for name, code in funcs:
                all_extracted.append(
                    {
                        "name": f"logichive_{name.lower().replace('.', '_')}",
                        "code": code,
                        "description": f"LogicHiveプロジェクト内部から抽出されたモジュール化ロジック: {name} ({rel_path})",
                        "tags": [
                            "internal",
                            "logichive",
                            rel_path.split("/")[0],
                            name.split(".")[0].lower(),
                        ],
                        "language": "python",
                    }
                )

    print(f"Total logic units found: {len(all_extracted)}")

    for f in all_extracted:
        # Avoid registering overly simple helpers or dunder methods
        if f["name"].endswith("__init__") or len(f["code"].splitlines()) < 3:
            continue

        print(f"Registering: {f['name']}...")
        try:
            # We don't have perfect test_code for all, so we skip background validation in phase 1 for some
            success = await do_save_async(
                name=f["name"],
                code=f["code"],
                description=f["description"],
                tags=f["tags"],
                language=f["language"],
                dependencies=[],  # Dependencies will be extracted by save_async automatically
            )
            if success:
                print("  [OK]")
            else:
                print("  [SKIP/FAIL]")
        except Exception as e:
            print(f"  [ERROR] {e}")


if __name__ == "__main__":
    asyncio.run(populate())
