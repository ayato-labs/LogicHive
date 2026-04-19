import random
import time
from typing import Any


async def run_strategic_site_scan(
    site_clients: dict[str, Any], scan_jobs: list[tuple[str, bool, str]], limit: int = 50
):
    """
    「なろう」「ハーメルン」等の複数小説投稿サイトに対し、
    ランキング種別（通常・R18）や条件を組み合わせて戦略的に広域スキャンを行う。
    サーバー負荷に配慮したランダムウェイト付きのクロール制御ロジック。
    """
    results = []
    for site_id, is_r18, job_type in scan_jobs:
        client = site_clients.get(site_id)
        if not client:
            continue

        # サイトごとのランキング取得（実装に依存）
        novels = await client.get_ranking(limit=limit, is_r18=is_r18)
        results.extend(novels)

        # Anti-scraping measure: サーバー負荷への配慮
        time.sleep(random.uniform(2.0, 5.0))

    return results
