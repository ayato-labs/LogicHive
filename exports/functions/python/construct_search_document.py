    def construct_search_document(
        self, name: str, description: str, tags: List[str], code: str
    ) -> str:
        """
        Constructs a structured document for embedding to maximize RAG relevance.
        Prioritizes semantic metadata while preserving logic context from the code.
        """
        # Document Structure: Title -> Semantic Spec -> Tags -> Implementation
        tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
        doc = (
            f"LOGIC ASSET: {name}\n"
            f"TECHNICAL SPECIFICATION:\n{description}\n"
            f"TAGS: {tags_str}\n"
            f"--- IMPLEMENTATION DETALS ---\n"
            f"{code}"
        )
        # Note: generate_embedding will handle the final 7,000 char (2048 token) truncation.
        return doc
