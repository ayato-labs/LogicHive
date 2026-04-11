from typing import Optional
from sqlalchemy.orm import Session

class VectorServiceWrapper:
    """
    High-level service wrapper for managing vector indexing and retrieval for novels.
    """
    def __init__(self, config, manager):
        self.config = config
        self.manager = manager

    async def index_novel(self, novel_obj: Any, db: Optional[Session] = None):
        """特定の作品のメタデータをインデックスに登録または更新する"""
        try:
            # 1. メタデータの更新
            await self.manager.index_novel_metadata(novel_obj)
            # 2. 本文の差分更新 (お気に入り or 読書中の場合のみ)
            if novel_obj.preference == 1 or novel_obj.reading_status == 1:
                await self.manager.index_novel_body_incremental(novel_obj, db)
        except Exception as e:
            raise e

    async def search(self, query: str, limit: int = 50):
        return await self.manager.search_similar_metadata(query, limit=limit)
