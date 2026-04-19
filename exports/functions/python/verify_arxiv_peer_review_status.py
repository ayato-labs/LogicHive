class ArxivTrustClassifier:
    """
    Hybrid classifier for arXiv peer-review status.
    Uses metadata (journal_ref, comment) and LLM inference as a fallback.
    """

    def __init__(self, gemini_service):
        self.gemini_service = gemini_service

    async def classify(self, title: str, comment: str, journal_ref: str):
        # 1. Metadata Heuristic
        metadata_vetted = journal_ref != "N/A" or any(
            kw in comment.lower()
            for kw in ["accepted", "published", "proceedings", "conference", "journal"]
        )

        # 2. LLM Inference
        prompt = f"Analyze if published in peer-reviewed venue.\nTitle: {title}\nComment: {comment}\nRef: {journal_ref}"
        schema = {
            "type": "OBJECT",
            "properties": {
                "is_peer_reviewed": {"type": "BOOLEAN"},
                "vetted_venue": {"type": "STRING", "nullable": True},
                "confidence": {"type": "NUMBER"},
                "reason": {"type": "STRING"},
            },
            "required": ["is_peer_reviewed", "vetted_venue", "confidence", "reason"],
        }

        result = await self.gemini_service.call_structured_async(
            prompt, response_schema=schema, tier="light"
        )
        result["metadata_heuristic"] = metadata_vetted
        return result
