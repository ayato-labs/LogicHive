from typing import List, Dict, Any, Optional
import re

class LiteratureReranker:
    """
    A specialized LLM-based reranker for creative writing context.
    Reranks documents based on their relevance to a literary query.
    """
    def __init__(self, client, model: str = "gemini-2.0-flash"):
        self.client = client
        self.model = model

    async def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[str]:
        if not documents:
            return []
        
        if len(documents) <= top_k:
            return documents

        doc_list_str = "\n".join([f"[{i}] {doc[:500]}..." for i, doc in enumerate(documents)])
        
        prompt = f"""
あなたは超一流の文芸編集者です。
与えられた「検索クエリ」に対して、以下の「情報リスト」の中から、物語の執筆に最も役立つと思われる上位{top_k}個を順に選んでください。

【検索クエリ】
{query}

【情報リスト】
{doc_list_str}

【指示】
- クエリ（現在の文脈や設定）との整合性が高いものを優先してください。
- 出力は、選んだドキュメントのインデックス番号をカンマ区切りで、優先順位が高い順に並べてください（例: 3, 0, 5）。
- 番号以外は何も出力しないでください。
"""
        try:
            response = await self.client.generate_content(
                model=self.model,
                contents=prompt
            )
            text = response.text.strip()
            indices = [int(i.strip()) for i in re.findall(r'\d+', text)]
            
            reranked = []
            for idx in indices:
                if 0 <= idx < len(documents):
                    reranked.append(documents[idx])
                if len(reranked) >= top_k:
                    break
            
            if not reranked:
                return documents[:top_k]
                
            return reranked
            
        except Exception:
            return documents[:top_k]
