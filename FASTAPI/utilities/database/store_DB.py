import logging
from typing import List, Dict, Any
from utilities.metadata import clean_metadata
import json

from .supabase_connect import db_connect

async def store_embedded_files(embedded_chunks: List[Dict[str, Any]]) -> str:
    """
    Store embedded chunks in Supabase (Postgres + pgvector)
    Chroma-equivalent behavior.
    
    """
    conn = await db_connect()

    try:
        for chunk in embedded_chunks:
            chunk_id = chunk["metadata"]["chunk_uuid"]
            text = chunk["page_content"]

            embeddin = (
                chunk["embedding"].tolist()
                if hasattr(chunk["embedding"], "tolist")
                else chunk["embedding"]
            )
            
            embedding = f"[{','.join(map(str, embeddin))}]"

            #metadata = clean_metadata(chunk.get("metadata", {}))
            
            metadata = json.dumps(clean_metadata(chunk.get("metadata", {})))

            await conn.execute(
            
                    """
                INSERT INTO documents (id, text, embedding, metadata)
                VALUES ($1, $2, $3::vector, $4)
                ON CONFLICT (id) DO NOTHING
                """,
                chunk_id,
                text,
                embedding,
                metadata,
            )

        logging.info(f"Stored {len(embedded_chunks)} chunks in Supabase")
        return f"Successfully stored {len(embedded_chunks)} chunks"

    except Exception as e:
        logging.error(f"Failed to store chunks: {e}")
        raise

    finally:
        await conn.close()
