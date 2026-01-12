from .supabase_connect import db_connect

async def query_supabase(embedded_prompt, n_results: int = 4):
    """
    Supabase-backed replacement for collection.query()
    Returns Chroma-compatible structure.
    """
    conn = await db_connect()

    try:
        # Normalize input
        if hasattr(embedded_prompt, "tolist"):
            embedded_prompt = embedded_prompt.tolist()

        if isinstance(embedded_prompt[0], (list, tuple)):
            query_embedding = embedded_prompt[0]
        else:
            query_embedding = embedded_prompt

        # Convert to pgvector literal
        query_embedding_str = f"[{','.join(map(str, query_embedding))}]"

        rows = await conn.fetch(
            """
            SELECT
                text,
                metadata,
                embedding <=> $1::vector AS distance
            FROM documents
            ORDER BY distance ASC
            LIMIT $2
            """,
            query_embedding_str,
            n_results,
        )

        # Chroma-compatible shape
        return {
            "documents": [[r["text"] for r in rows]],
            "distances": [[r["distance"] for r in rows]],
            "metadatas": [[r["metadata"] for r in rows]],
        }

    finally:
        await conn.close()
