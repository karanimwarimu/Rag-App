from supabase_connect import db_connect

async def query_chroma(embedded_prompt, n_results: int = 4):
    """
    Supabase-backed replacement for collection.query()
    Returns Chroma-compatible structure.
    """
    conn = await db_connect()

    try:
        # Normalize embedding input
        if not isinstance(embedded_prompt[0], (list, tuple)):
            embedded_prompt = [embedded_prompt]

        query_embedding = embedded_prompt[0]

        rows = await conn.fetch(
            """
            SELECT
                text,
                metadata,
                embedding <=> $1 AS distance
            FROM documents
            ORDER BY distance ASC
            LIMIT $2
            """,
            query_embedding,
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
