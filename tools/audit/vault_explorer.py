import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from orchestrator import do_list_async
import pandas as pd

async def main():
    print("\n" + "="*60)
    print(" LOGICHIVE VAULT EXPLORER")
    print("="*60 + "\n")

    project = None
    if len(sys.argv) > 1:
        project = sys.argv[1]
        print(f"Filtering by project: {project}")

    results = await do_list_async(project=project, limit=100)

    if not results:
        print("No functions found in the vault.")
        return

    # Prepare data for DataFrame
    data = []
    for res in results:
        data.append({
            "Name": res["name"],
            "Project": res.get("project", "default"),
            "Lang": res.get("language", "py"),
            "Reliability": f"{res.get('reliability_score', 0)*100:.1f}%",
            "Tags": ", ".join(res.get("tags", [])),
            "Updated": res.get("updated_at", "N/A")
        })

    df = pd.DataFrame(data)
    
    # Configure pandas display
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.colheader_justify', 'left')
    
    print(df.to_string(index=False))
    print(f"\nTotal Assets: {len(results)}")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
