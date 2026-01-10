import numpy as np

# -------------------------
# Rerank chunks
# -------------------------
async def rerank_chunks(chunks, query_embedding, embeddings_fn, top_k=3):
    """
    Re-rank chunks by cosine similarity with the query.
    Args:
        chunks (list[str])
        query_embedding (list[float])
        embeddings_fn (callable): async embedding function
    Returns:
        list[str]
    """
    chunk_embeddings = [await embeddings_fn(c) for c in chunks]
    sims = [cosine_similarity(query_embedding, ce) for ce in chunk_embeddings]

    ranked = sorted(zip(chunks, sims), key=lambda x: x[1], reverse=True)
    return [c for c, _ in ranked[:top_k]]

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# -------------------------
# Token trimming
# -------------------------
async def trim_chunks(chunks, tokenizer, max_tokens=400):
    final = []
    for c in chunks:
        tokens = tokenizer.encode(c["text"])
        if len(tokens) > max_tokens:
            tokens = tokens[:max_tokens]
            trimmed_text = tokenizer.decode(tokens)
            final.append({"text": trimmed_text, "metadata": c.get("metadata", {})})
        else:
            final.append(c)
    return final



async def filter_and_trim_chunks(chunks, query_embedding, embeddings_fn, tokenizer, max_tokens=500, top_k=5, min_sim=0.7):
    # 1️⃣ Embed and compute similarity
    chunk_embeddings = [await embeddings_fn(c) for c in chunks]
    sims = [cosine_similarity(query_embedding, ce) for ce in chunk_embeddings]

    # 2️⃣ Filter by threshold & rank
    ranked = sorted([(c, s) for c, s in zip(chunks, sims) if s >= min_sim], key=lambda x: x[1], reverse=True)
    
    # 3️⃣ Trim to token budget
    total, trimmed = 0, []
    for c, _ in ranked[:top_k]:
        tokens = tokenizer.encode(c)
        if total + len(tokens) > max_tokens:
            # optional: truncate chunk to fit remaining tokens
            remaining_tokens = max_tokens - total
            if remaining_tokens <= 0:
                break
            c = tokenizer.decode(tokens[:remaining_tokens])
            trimmed.append(c)
            break
        trimmed.append(c)
        total += len(tokens)
    return trimmed
